"""
Execution Agent — submits approved trades to exchanges.
Model: google/gemma-4-26b-a4b:free (fast, function calling support)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from agents.base_agent import BaseAgent
from core.config import settings
from core.database import AsyncSessionLocal
from core.message_bus import AgentMessage, MessageBus, MessageType

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    name = "execution"
    model = settings.model_execution

    def __init__(self, bus: MessageBus) -> None:
        super().__init__(bus)
        self._polymarket = None
        self._hyperliquid = None

    async def startup(self) -> None:
        from integrations.hyperliquid import hyperliquid_client
        from integrations.polymarket import polymarket_client
        self._polymarket = polymarket_client
        self._hyperliquid = hyperliquid_client
        await self.update_status("idle", "Execution agent ready (paper mode)" if not settings.trading_enabled else "Execution agent ready (LIVE)")

    async def handle_message(self, msg: AgentMessage) -> None:
        if msg.message_type == MessageType.MASTER_DECISION:
            decision = msg.payload.get("decision", {})
            if decision.get("action") == "execute":
                await self._execute_trade(msg)

    async def _execute_trade(self, msg: AgentMessage) -> None:
        decision = msg.payload.get("decision", {})
        thesis = msg.payload.get("thesis", {})
        review = msg.payload.get("review", {})

        market = thesis.get("market", "Unknown")
        exchange = thesis.get("exchange", "unknown")

        await self.update_status("thinking", f"Executing trade on {market}...")
        logger.info("Execution agent: %s %s on %s", thesis.get("direction"), market, exchange)

        trade_id = str(uuid.uuid4())[:8]
        result = {}

        try:
            exchange_enabled = await self._exchange_enabled(exchange)
            live = settings.trading_enabled and exchange_enabled

            if not live:
                reason = "trading_enabled=false" if not settings.trading_enabled else f"{exchange} disabled"
                real_price = await self._fetch_current_price(exchange, thesis)
                result = {
                    "status": "paper",
                    "trade_id": trade_id,
                    "market": market,
                    "exchange": exchange,
                    "direction": thesis.get("direction"),
                    "size_pct": review.get("approved_size_pct", 1.0),
                    "entry_price": real_price or thesis.get("suggested_entry"),
                    "stop_loss": review.get("stop_loss"),
                    "take_profit": review.get("take_profit"),
                    "message": f"PAPER TRADE — {reason}. Real price: {real_price}",
                }
                logger.info("PAPER TRADE (%s): %s", reason, json.dumps(result))
            else:
                # Live execution
                if exchange == "hyperliquid":
                    result = await self._execute_hyperliquid(thesis, review)
                elif exchange == "polymarket":
                    result = await self._execute_polymarket(thesis, review)
                else:
                    result = {"status": "failed", "error": f"Unknown exchange: {exchange}"}

            # Persist trade to DB
            await self._save_trade(msg.round_id, thesis, review, result)

            await self.publish(
                to_agent="all",
                message_type=MessageType.EXECUTION_REPORT,
                payload={"result": result, "thesis": thesis},
                round_id=msg.round_id,
            )

            status = result.get("status", "unknown")
            await self.update_status("idle", f"Execution complete: {market} → {status}")

        except Exception as e:
            logger.error("Execution error: %s", e)
            error_result = {"status": "failed", "error": str(e), "market": market}

            await self.publish(
                to_agent="all",
                message_type=MessageType.EXECUTION_REPORT,
                payload={"result": error_result, "thesis": thesis, "failed": True},
                round_id=msg.round_id,
            )

            # Trigger self-correction
            await self.publish(
                to_agent="all",
                message_type=MessageType.SELF_CORRECTION,
                payload={"error": str(e), "thesis": thesis, "exchange": exchange},
                round_id=msg.round_id,
            )
            await self.update_status("error", f"Execution failed: {str(e)[:100]}")

    async def _exchange_enabled(self, exchange: str) -> bool:
        """Check per-exchange toggle from system_config DB."""
        from sqlalchemy import select
        from models.portfolio import SystemConfig
        key = f"{exchange}_enabled"
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
                row = result.scalar_one_or_none()
                return row.value == "true" if row else True  # default: enabled
        except Exception:
            return True

    async def _fetch_current_price(self, exchange: str, thesis: dict) -> float | None:
        """Fetch real current price for paper trade entry."""
        try:
            market = thesis.get("market", "")
            if exchange == "hyperliquid" and self._hyperliquid:
                info = await self._hyperliquid.get_market_info(market)
                return info.get("mid_price") or info.get("mark_price")
            elif exchange == "polymarket" and self._polymarket:
                market_id = thesis.get("market_id", "")
                prices = await self._polymarket.get_market_prices(market_id)
                return prices.get("yes_price") or prices.get("best_bid")
        except Exception as e:
            logger.warning("Could not fetch real price for paper trade: %s", e)
        return thesis.get("suggested_entry")

    async def _execute_hyperliquid(self, thesis: dict, review: dict) -> dict:
        direction = thesis.get("direction", "")
        market = thesis.get("market", "")
        is_buy = "long" in direction.lower() or "buy" in direction.lower()

        result = await self._hyperliquid.place_order(
            coin=market,
            is_buy=is_buy,
            size=review.get("approved_size_pct", 1.0),
            price=thesis.get("suggested_entry"),
            stop_loss=review.get("stop_loss"),
            take_profit=review.get("take_profit"),
        )
        return result

    async def _execute_polymarket(self, thesis: dict, review: dict) -> dict:
        direction = thesis.get("direction", "")
        market_id = thesis.get("market_id", "")
        is_yes = "buy" in direction.lower() or "yes" in direction.lower()

        result = await self._polymarket.place_order(
            market_id=market_id,
            is_yes=is_yes,
            size_pct=review.get("approved_size_pct", 2.0),
            price=thesis.get("suggested_entry"),
        )
        return result

    async def _save_trade(self, round_id: str, thesis: dict, review: dict, result: dict) -> None:
        from models.trade import Trade

        try:
            async with AsyncSessionLocal() as session:
                trade = Trade(
                    round_id=round_id,
                    exchange=thesis.get("exchange", "unknown"),
                    market=thesis.get("market", ""),
                    direction=thesis.get("direction", ""),
                    size=review.get("approved_size_pct"),
                    entry_price=thesis.get("suggested_entry"),
                    status=result.get("status", "pending"),
                    order_id=result.get("order_id") or result.get("trade_id"),
                    opened_at=datetime.utcnow() if result.get("status") not in ("failed", "dry_run") else None,
                )
                session.add(trade)
                await session.commit()
        except Exception as e:
            logger.error("Failed to save trade: %s", e)
