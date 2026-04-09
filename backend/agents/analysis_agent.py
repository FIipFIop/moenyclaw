"""
Analysis Agent — builds full trade thesis for opportunities.
Model: google/gemma-4-31b:free (256K context, thinking mode)
"""
from __future__ import annotations

import json
import logging

from agents.base_agent import BaseAgent
from core.config import settings
from core.message_bus import AgentMessage, MessageBus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a quantitative trading analyst. You receive trading opportunities and produce a detailed analysis thesis.

For each opportunity, provide a JSON object with:
{
  "market": "<market name>",
  "exchange": "<exchange>",
  "direction": "<direction>",
  "thesis": "<3-5 sentence analysis>",
  "supporting_factors": ["<factor1>", "<factor2>", "<factor3>"],
  "risks": ["<risk1>", "<risk2>"],
  "confidence_score": <0.0 to 1.0>,
  "suggested_entry": <price float>,
  "suggested_stop_loss": <price float>,
  "suggested_take_profit": <price float>,
  "position_size_pct": <recommended % of portfolio 0-10>,
  "expected_return_pct": <expected return %>
}

Be rigorous. If the opportunity is weak, say so with a low confidence score."""


class AnalysisAgent(BaseAgent):
    name = "analysis"
    model = settings.model_analysis

    def __init__(self, bus: MessageBus) -> None:
        super().__init__(bus)

    async def startup(self) -> None:
        await self.update_status("idle", "Analysis agent ready")

    async def handle_message(self, msg: AgentMessage) -> None:
        if msg.message_type == MessageType.OPPORTUNITY:
            await self._analyze_opportunity(msg)
        elif msg.message_type == MessageType.DEBATE_CHALLENGE:
            await self._respond_to_debate(msg)

    async def _analyze_opportunity(self, msg: AgentMessage) -> None:
        opp = msg.payload.get("opportunity", {})
        market = opp.get("market", "Unknown")

        await self.update_status("thinking", f"Analyzing {market}...")
        logger.info("Analysis agent processing opportunity: %s", market)

        try:
            user_prompt = f"""Analyze this trading opportunity in depth:

{json.dumps(opp, indent=2)}

Provide a comprehensive trade thesis in JSON format."""

            response = await self.call_llm(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.2,
                max_tokens=2000,
            )

            thesis = self._extract_json(response)
            if not thesis:
                thesis = {"market": market, "error": "LLM parsing failed", "confidence_score": 0.0}

            await self.publish(
                to_agent="all",
                message_type=MessageType.ANALYSIS,
                payload={"thesis": thesis, "original_opportunity": opp},
                round_id=msg.round_id,
            )

            await self.update_status("waiting", f"Analysis of {market} published — awaiting review")

        except Exception as e:
            logger.error("Analysis error for %s: %s", market, e)
            await self.update_status("error", f"Analysis failed: {str(e)[:100]}")

    async def _respond_to_debate(self, msg: AgentMessage) -> None:
        """Revise thesis based on debate agent's challenge."""
        challenge = msg.payload.get("challenge", "")
        original_thesis = msg.payload.get("original_thesis", {})
        market = original_thesis.get("market", "Unknown")

        await self.update_status("thinking", f"Revising thesis for {market} after debate challenge")

        try:
            user_prompt = f"""You previously produced this analysis:
{json.dumps(original_thesis, indent=2)}

The debate agent raised these concerns:
{challenge}

Revise your analysis addressing these concerns. If the concerns are valid, lower your confidence score accordingly.
Output a revised JSON thesis."""

            response = await self.call_llm(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.3,
                max_tokens=2000,
            )

            revised = self._extract_json(response)
            if not revised:
                revised = original_thesis

            await self.publish(
                to_agent="risk",
                message_type=MessageType.ANALYSIS,
                payload={"thesis": revised, "revised": True, "debate_addressed": challenge[:200]},
                round_id=msg.round_id,
            )

            await self.update_status("waiting", f"Revised thesis for {market} sent to risk agent")

        except Exception as e:
            logger.error("Revision error: %s", e)

    def _extract_json(self, text: str) -> dict | None:
        text = text.strip()
        # Try to find a JSON object in the response
        for start_char, end_char in [('{', '}')]:
            start = text.find(start_char)
            end = text.rfind(end_char) + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        try:
            return json.loads(text)
        except Exception:
            return None
