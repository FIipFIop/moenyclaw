"""
Hyperliquid integration wrapper.
Uses hyperliquid-python-sdk for account management and trading.
"""
from __future__ import annotations

import logging
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)


class HyperliquidClient:
    def __init__(self) -> None:
        self._exchange = None
        self._info = None
        self._address = settings.hyperliquid_address
        self._ready = False

    def _init_sdk(self) -> None:
        if self._ready:
            return
        try:
            from eth_account import Account
            from hyperliquid.exchange import Exchange
            from hyperliquid.info import Info
            from hyperliquid.utils import constants

            base_url = (
                constants.MAINNET_API_URL
                if settings.hyperliquid_network == "mainnet"
                else constants.TESTNET_API_URL
            )

            wallet = Account.from_key(settings.hyperliquid_private_key)
            self._info = Info(base_url, skip_ws=True)
            self._exchange = Exchange(wallet, base_url, account_address=self._address)
            self._ready = True
            logger.info("Hyperliquid client initialized (%s)", settings.hyperliquid_network)
        except Exception as e:
            logger.error("Hyperliquid SDK init failed: %s", e)
            self._ready = False

    async def get_balance(self) -> dict[str, float]:
        """Return account balance info."""
        try:
            self._init_sdk()
            if not self._ready or not self._info:
                return {"equity": 0.0, "available": 0.0, "unrealized_pnl": 0.0}

            # SDK calls are synchronous — run in executor if needed
            import asyncio
            loop = asyncio.get_event_loop()
            state = await loop.run_in_executor(None, self._info.user_state, self._address)

            margin = state.get("marginSummary", {})
            return {
                "equity": float(margin.get("accountValue", 0)),
                "available": float(margin.get("withdrawable", 0)),
                "unrealized_pnl": float(margin.get("totalUnrealizedPnl", 0)),
            }
        except Exception as e:
            logger.error("Hyperliquid get_balance error: %s", e)
            return {"equity": 0.0, "available": 0.0, "unrealized_pnl": 0.0}

    async def get_open_positions(self) -> list[dict]:
        """Return current open perp positions."""
        try:
            self._init_sdk()
            if not self._ready or not self._info:
                return []

            import asyncio
            loop = asyncio.get_event_loop()
            state = await loop.run_in_executor(None, self._info.user_state, self._address)
            positions = state.get("assetPositions", [])

            result = []
            for pos in positions:
                p = pos.get("position", {})
                if float(p.get("szi", 0)) != 0:
                    result.append({
                        "coin": p.get("coin"),
                        "size": float(p.get("szi", 0)),
                        "entry_price": float(p.get("entryPx", 0)),
                        "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
                        "leverage": p.get("leverage", {}),
                    })
            return result
        except Exception as e:
            logger.error("Hyperliquid get_positions error: %s", e)
            return []

    async def get_market_summary(self) -> list[dict]:
        """Get top markets by volume for research agent."""
        try:
            self._init_sdk()
            if not self._ready or not self._info:
                return []

            import asyncio
            loop = asyncio.get_event_loop()
            meta = await loop.run_in_executor(None, self._info.meta_and_asset_ctxs)
            universe = meta[0].get("universe", [])
            ctxs = meta[1]

            markets = []
            for i, asset in enumerate(universe[:30]):
                ctx = ctxs[i] if i < len(ctxs) else {}
                markets.append({
                    "name": asset.get("name"),
                    "mark_price": float(ctx.get("markPx", 0)),
                    "funding": float(ctx.get("funding", 0)),
                    "open_interest": float(ctx.get("openInterest", 0)),
                    "day_change_pct": float(ctx.get("dayNtlVlm", 0)),
                })

            # Sort by open interest descending
            markets.sort(key=lambda x: x["open_interest"], reverse=True)
            return markets[:15]

        except Exception as e:
            logger.error("Hyperliquid get_market_summary error: %s", e)
            return []

    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict[str, Any]:
        """Place a market order on Hyperliquid."""
        if not settings.trading_enabled:
            return {"status": "dry_run", "message": "Trading disabled"}

        try:
            self._init_sdk()
            if not self._ready or not self._exchange:
                return {"status": "failed", "error": "Hyperliquid not initialized"}

            import asyncio
            loop = asyncio.get_event_loop()

            order_type = {"limit": {"tif": "Ioc"}} if price else {"market": {}}
            order_price = price or 0

            result = await loop.run_in_executor(
                None,
                lambda: self._exchange.order(
                    coin,
                    is_buy,
                    size,
                    order_price,
                    order_type,
                    reduce_only=False,
                ),
            )

            order_id = None
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses:
                    order_id = str(statuses[0].get("resting", {}).get("oid", ""))

            return {
                "status": "open" if result.get("status") == "ok" else "failed",
                "order_id": order_id,
                "raw": result,
            }

        except Exception as e:
            logger.error("Hyperliquid place_order error: %s", e)
            return {"status": "failed", "error": str(e)}

    async def close_position(self, coin: str) -> dict[str, Any]:
        """Market-close an open position."""
        if not settings.trading_enabled:
            return {"status": "dry_run"}
        try:
            self._init_sdk()
            if not self._ready or not self._exchange:
                return {"status": "failed", "error": "Not initialized"}

            import asyncio
            positions = await self.get_open_positions()
            pos = next((p for p in positions if p["coin"] == coin), None)
            if not pos:
                return {"status": "failed", "error": f"No open position for {coin}"}

            size = abs(pos["size"])
            is_buy = pos["size"] < 0  # buy to close a short

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._exchange.order(
                    coin, is_buy, size, 0, {"market": {}}, reduce_only=True
                ),
            )
            return {"status": "closed" if result.get("status") == "ok" else "failed", "raw": result}

        except Exception as e:
            logger.error("Hyperliquid close_position error: %s", e)
            return {"status": "failed", "error": str(e)}


hyperliquid_client = HyperliquidClient()
