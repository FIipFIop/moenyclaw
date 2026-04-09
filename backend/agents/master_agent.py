"""
Master Agent — orchestrates all agents, makes final trading decisions.
Model: nvidia/nemotron-3-super:free (1M context, built for multi-agent orchestration)
"""
from __future__ import annotations

import json
import logging

from agents.base_agent import BaseAgent
from core.config import settings
from core.message_bus import AgentMessage, MessageBus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the master orchestrator of a crypto trading agent network.

You receive risk reviews and make FINAL decisions on whether to execute trades.
You have access to the full context: research opportunity, analysis thesis, debate challenge, and risk review.

Consider:
1. The risk agent's decision (most important)
2. The analysis confidence score
3. The debate agent's verdict
4. Current market conditions

Output a JSON object:
{
  "action": "execute" | "skip",
  "reason": "<explanation>",
  "confidence": <0.0 to 1.0>,
  "notes": "<any final notes for the execution agent>"
}

If the risk agent rejected the trade, you should almost always skip it.
If risk approved, use your judgment based on the full picture."""


class MasterAgent(BaseAgent):
    name = "master"
    model = settings.model_master

    def __init__(self, bus: MessageBus) -> None:
        super().__init__(bus)
        self._pending_rounds: dict[str, dict] = {}  # round_id → accumulated context

    async def startup(self) -> None:
        await self.update_status("idle", "Master agent online — commanding the network")

    async def handle_message(self, msg: AgentMessage) -> None:
        round_id = msg.round_id

        if msg.message_type == MessageType.USER_PROMPT:
            await self._handle_user_prompt(msg)

        elif msg.message_type == MessageType.OPPORTUNITY:
            # New opportunity — initialize round context and forward to analysis
            self._pending_rounds[round_id] = {
                "opportunity": msg.payload.get("opportunity", {}),
                "analysis": None,
                "debate": None,
                "risk_review": None,
            }
            logger.info("Master: new opportunity round %s", round_id[:8])
            await self.update_status("thinking", f"New opportunity: {msg.payload.get('opportunity', {}).get('market', 'Unknown')}")

        elif msg.message_type == MessageType.ANALYSIS and not msg.payload.get("revised"):
            # Store first analysis — debate agent handles challenging it
            if round_id in self._pending_rounds:
                self._pending_rounds[round_id]["analysis"] = msg.payload.get("thesis")

        elif msg.message_type == MessageType.RISK_REVIEW:
            # We have the full picture — make the final call
            if round_id in self._pending_rounds:
                self._pending_rounds[round_id]["risk_review"] = msg.payload.get("review", {})
                await self._make_decision(msg)

        elif msg.message_type == MessageType.EXECUTION_REPORT:
            # Log result, clean up round
            result = msg.payload.get("result", {})
            logger.info(
                "Master: execution report for round %s — status: %s",
                round_id[:8],
                result.get("status"),
            )
            if msg.payload.get("failed"):
                await self.update_status("thinking", "Execution failed — triggering self-correction analysis")
            self._pending_rounds.pop(round_id, None)

        elif msg.message_type == MessageType.SELF_CORRECTION:
            await self._handle_self_correction(msg)

    async def _make_decision(self, msg: AgentMessage) -> None:
        round_id = msg.round_id
        context = self._pending_rounds.get(round_id, {})
        review = msg.payload.get("review", {})
        thesis = msg.payload.get("thesis", {})
        market = thesis.get("market", "Unknown")

        await self.update_status("thinking", f"Master making final decision on {market}...")

        try:
            user_prompt = f"""Make a final trading decision based on this complete context:

OPPORTUNITY:
{json.dumps(context.get('opportunity', {}), indent=2)}

ANALYSIS THESIS:
{json.dumps(thesis, indent=2)}

RISK REVIEW:
{json.dumps(review, indent=2)}

The risk agent's decision was: {review.get('decision', 'unknown')}
Risk notes: {review.get('notes', 'none')}

Make the final call."""

            response = await self.call_llm(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.1,
                max_tokens=500,
            )

            decision = self._extract_json(response) or {
                "action": "skip",
                "reason": "Could not parse LLM decision",
                "confidence": 0.0,
            }

            # Hard override: if risk rejected, skip unless very compelling
            if review.get("decision") == "rejected" and decision.get("confidence", 0) < 0.85:
                decision["action"] = "skip"
                decision["reason"] = f"Risk rejected: {review.get('rejection_reason', 'Unknown reason')}"

            logger.info("Master decision for %s: %s", market, decision.get("action"))

            await self.publish(
                to_agent="execution",
                message_type=MessageType.MASTER_DECISION,
                payload={
                    "decision": decision,
                    "thesis": thesis,
                    "review": review,
                },
                round_id=round_id,
            )

            # Also broadcast decision to all (for dashboard)
            await self.publish(
                to_agent="all",
                message_type=MessageType.MASTER_DECISION,
                payload={
                    "decision": decision,
                    "thesis": {"market": market, "exchange": thesis.get("exchange")},
                    "broadcast": True,
                },
                round_id=round_id,
            )

            status = "execute" if decision.get("action") == "execute" else "skip"
            await self.update_status("idle", f"Decision on {market}: {status}")

        except Exception as e:
            logger.error("Master decision error: %s", e)
            await self.update_status("error", f"Decision error: {str(e)[:100]}")

    async def _handle_user_prompt(self, msg: AgentMessage) -> None:
        """Process a direct prompt from the dashboard user."""
        text = msg.payload.get("text", "").strip()
        if not text:
            return

        await self.update_status("thinking", f"User asked: {text[:80]}")
        logger.info("Master handling user prompt: %s", text[:100])

        # Check for shortcut commands first (no LLM needed)
        lower = text.lower()
        if any(k in lower for k in ["scan", "research", "find opportunities", "look for trades"]):
            await self.update_status("thinking", "Triggering research scan per user request...")
            await self.trigger_research_scan()
            await self.publish(
                to_agent="all",
                message_type=MessageType.STATUS_UPDATE,
                payload={"text": "Research scan triggered by user.", "from": "master"},
                round_id=msg.round_id,
            )
            await self.update_status("idle", "Research scan triggered")
            return

        # Otherwise: ask the LLM to respond and optionally take action
        try:
            response = await self.call_llm(
                system="""You are the master agent of a crypto trading network.
The user is communicating with you directly via the dashboard.
Respond helpfully and concisely. You can:
- Answer questions about markets, trading strategy, or agent activity
- Explain what the agents are doing
- Suggest next steps
- If the user asks you to trade, scan, analyze, or do something actionable, say what action you would take

Keep responses under 150 words. Be direct.""",
                user=text,
                temperature=0.6,
                max_tokens=300,
            )

            await self.publish(
                to_agent="all",
                message_type=MessageType.STATUS_UPDATE,
                payload={"text": response, "from": "master", "reply_to_user": True},
                round_id=msg.round_id,
            )
            await self.update_status("idle", f"Replied to user: {response[:80]}")

        except Exception as e:
            logger.error("User prompt error: %s", e)
            await self.update_status("error", f"Could not process prompt: {str(e)[:80]}")

    async def _handle_self_correction(self, msg: AgentMessage) -> None:
        """Analyze a failed trade and log lessons learned."""
        error = msg.payload.get("error", "")
        thesis = msg.payload.get("thesis", {})
        market = thesis.get("market", "Unknown")

        await self.update_status("thinking", f"Self-correction analysis for {market}...")

        try:
            response = await self.call_llm(
                system="You are a trading post-mortem analyst. Analyze why a trade failed and extract key lessons.",
                user=f"""A trade on {market} failed with error: {error}

Trade thesis was:
{json.dumps(thesis, indent=2)}

What went wrong? What should we avoid in the future?
Be brief (3-5 bullet points).""",
                temperature=0.4,
                max_tokens=500,
            )

            logger.info("Self-correction for %s: %s", market, response[:200])
            await self.update_status("idle", f"Self-correction complete for {market}")

        except Exception as e:
            logger.error("Self-correction analysis failed: %s", e)

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

    async def trigger_research_scan(self) -> None:
        """Trigger a research scan via the bus (scheduler, user prompt, or post-cycle)."""
        import uuid
        logger.info("Master triggering research scan")
        await self.update_status("thinking", "Triggering research scan...")
        # Publish a special internal message that research agent listens for
        await self.publish(
            to_agent="research",
            message_type=MessageType.STATUS_UPDATE,
            payload={"action": "scan", "round_id": str(uuid.uuid4())},
        )
        await self.update_status("idle", "Research scan triggered")
