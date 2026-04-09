"""
Risk Agent — reviews trades, sets position sizes, rejects bad trades.
Model: nvidia/nemotron-3-super:free (complex multi-step reasoning)
"""
from __future__ import annotations

import json
import logging

from agents.base_agent import BaseAgent
from core.config import settings
from core.message_bus import AgentMessage, MessageBus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict risk management officer for a crypto trading fund.

Your job: review trade theses and make final sizing/approval decisions.

Rules:
- Never approve trades with confidence < 0.55
- Maximum position size: 10% of portfolio
- Minimum expected return must exceed 1.5x risk (stop-loss distance)
- If stop-loss is missing, reject the trade
- Maximum 3 open positions at a time
- Never bet more than 5% on prediction markets (Polymarket)

Output a JSON object:
{
  "market": "<market>",
  "decision": "approved" | "rejected" | "approved_reduced",
  "approved_size_pct": <0.0 to 10.0>,
  "rejection_reason": "<if rejected>",
  "risk_score": <0.0 to 1.0>,
  "max_loss_usd": <estimated max loss>,
  "notes": "<risk notes>",
  "stop_loss": <price>,
  "take_profit": <price>
}"""


class RiskAgent(BaseAgent):
    name = "risk"
    model = settings.model_risk

    def __init__(self, bus: MessageBus) -> None:
        super().__init__(bus)
        self._portfolio_value = 1000.0  # updated from DB at runtime

    async def startup(self) -> None:
        await self._refresh_portfolio_value()
        await self.update_status("idle", "Risk agent ready")

    async def handle_message(self, msg: AgentMessage) -> None:
        if msg.message_type == MessageType.ANALYSIS and msg.payload.get("revised"):
            await self._review_trade(msg)

    async def _review_trade(self, msg: AgentMessage) -> None:
        thesis = msg.payload.get("thesis", {})
        market = thesis.get("market", "Unknown")

        await self.update_status("thinking", f"Risk review for {market}...")
        logger.info("Risk agent reviewing: %s", market)

        try:
            await self._refresh_portfolio_value()

            user_prompt = f"""Review this trade thesis for risk:

Portfolio Value: ${self._portfolio_value:.2f}

Trade Thesis:
{json.dumps(thesis, indent=2)}

Apply the risk rules and output a decision in JSON format."""

            response = await self.call_llm(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.1,  # Very low temp — we want deterministic risk decisions
                max_tokens=1000,
            )

            review = self._extract_json(response)
            if not review:
                review = {
                    "market": market,
                    "decision": "rejected",
                    "rejection_reason": "Risk agent could not parse thesis",
                    "approved_size_pct": 0.0,
                }

            logger.info("Risk decision for %s: %s", market, review.get("decision"))

            await self.publish(
                to_agent="master",
                message_type=MessageType.RISK_REVIEW,
                payload={
                    "review": review,
                    "thesis": thesis,
                    "original_opportunity": msg.payload.get("original_opportunity", {}),
                },
                round_id=msg.round_id,
            )

            await self.update_status(
                "idle",
                f"Risk review: {market} → {review.get('decision', 'unknown')}",
            )

        except Exception as e:
            logger.error("Risk review error: %s", e)
            await self.update_status("error", f"Risk error: {str(e)[:100]}")

    async def _refresh_portfolio_value(self) -> None:
        try:
            from core.database import AsyncSessionLocal
            from models.portfolio import PortfolioSnapshot
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_at.desc()).limit(1)
                )
                snap = result.scalar_one_or_none()
                if snap:
                    self._portfolio_value = snap.total_usd or 1000.0
        except Exception:
            pass

    def _extract_json(self, text: str) -> dict | None:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
        return None
