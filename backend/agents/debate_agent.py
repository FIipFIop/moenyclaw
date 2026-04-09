"""
Debate Agent — devil's advocate; challenges trade theses.
Model: google/gemma-4-26b-a4b:free (efficient MoE)
"""
from __future__ import annotations

import json
import logging

from agents.base_agent import BaseAgent
from core.config import settings
from core.message_bus import AgentMessage, MessageBus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a contrarian trading analyst whose job is to challenge trading theses and find weaknesses.

When given a trade thesis, identify the strongest arguments AGAINST the trade:
1. What could go wrong?
2. What is the thesis missing?
3. Is the confidence score justified?
4. Are there macro/market risks not considered?

Output a JSON object:
{
  "market": "<market>",
  "challenge_strength": <0.0 to 1.0>,
  "key_challenges": ["<challenge1>", "<challenge2>", "<challenge3>"],
  "missed_risks": ["<risk1>", "<risk2>"],
  "verdict": "proceed" | "revise" | "abort",
  "suggested_confidence_adjustment": <-0.3 to 0.0>,
  "summary": "<2-3 sentence challenge summary>"
}

Be tough but fair. A verdict of "proceed" means the thesis holds up to scrutiny."""


class DebateAgent(BaseAgent):
    name = "debate"
    model = settings.model_debate

    def __init__(self, bus: MessageBus) -> None:
        super().__init__(bus)

    async def startup(self) -> None:
        await self.update_status("idle", "Debate agent ready")

    async def handle_message(self, msg: AgentMessage) -> None:
        if msg.message_type == MessageType.ANALYSIS:
            # Only challenge first (non-revised) analyses
            if not msg.payload.get("revised"):
                await self._challenge_thesis(msg)

    async def _challenge_thesis(self, msg: AgentMessage) -> None:
        thesis = msg.payload.get("thesis", {})
        market = thesis.get("market", "Unknown")

        await self.update_status("thinking", f"Challenging thesis for {market}...")
        logger.info("Debate agent challenging: %s", market)

        try:
            user_prompt = f"""Challenge this trading thesis:

{json.dumps(thesis, indent=2)}

Find the strongest arguments against this trade. Be rigorous."""

            response = await self.call_llm(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.5,
                max_tokens=1500,
            )

            challenge = self._extract_json(response)
            if not challenge:
                challenge = {
                    "market": market,
                    "verdict": "proceed",
                    "summary": "No significant challenges identified",
                    "challenge_strength": 0.2,
                }

            await self.publish(
                to_agent="analysis",
                message_type=MessageType.DEBATE_CHALLENGE,
                payload={
                    "challenge": challenge.get("summary", ""),
                    "full_challenge": challenge,
                    "original_thesis": thesis,
                    "verdict": challenge.get("verdict", "proceed"),
                },
                round_id=msg.round_id,
            )

            await self.update_status(
                "idle",
                f"Challenged {market} — verdict: {challenge.get('verdict', 'proceed')}",
            )

        except Exception as e:
            logger.error("Debate error: %s", e)
            await self.update_status("error", f"Debate failed: {str(e)[:100]}")

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
