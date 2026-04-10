"""
Research Agent — scans Polymarket and Hyperliquid for opportunities.
Model: minimax/minimax-m2.5:free (strong at data extraction & browsing tasks)
"""
from __future__ import annotations

import json
import logging

from agents.base_agent import BaseAgent
from core.config import settings
from core.message_bus import AgentMessage, MessageBus, MessageType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Polymarket short-term trading specialist. Your only goal is fast profit: find markets that are MISPRICED RIGHT NOW and will resolve or correct within hours to a few days.

WHAT TO LOOK FOR (quick flips only):
- Markets resolving within 24-72 hours where current price is clearly wrong
- Sports games, political votes, economic releases happening TODAY or TOMORROW
- Markets at extreme prices (< 0.15 or > 0.85) that are obviously too low/high
- High-volume markets where the crowd is wrong

IGNORE: anything resolving more than 1 week away. Ignore low-volume markets under $5k.

For each opportunity output a JSON object:
{
  "exchange": "polymarket",
  "market": "<short market name>",
  "market_id": "<condition_id from data>",
  "direction": "buy yes" or "buy no",
  "current_price": <float 0-1>,
  "fair_value": <your estimate 0-1>,
  "edge": <fair_value - current_price, positive means underpriced>,
  "confidence": <0.0 to 1.0>,
  "rationale": "<one sentence: why is this mispriced and when does it resolve>",
  "time_horizon": "<e.g. 6h, 12h, 24h, 48h>",
  "resolves_at": "<date or event>"
}

Only output opportunities where edge >= 0.08 AND confidence >= 0.65. Output a JSON array. Max 3 opportunities."""


class ResearchAgent(BaseAgent):
    name = "research"
    model = settings.model_research

    def __init__(self, bus: MessageBus) -> None:
        super().__init__(bus)
        self._polymarket = None
        self._hyperliquid = None

    async def startup(self) -> None:
        import asyncio
        from integrations.hyperliquid import hyperliquid_client
        from integrations.polymarket import polymarket_client
        self._polymarket = polymarket_client
        self._hyperliquid = hyperliquid_client
        await self.update_status("idle", "Research agent ready — starting initial scan...")
        # Kick off first scan after a short delay so all agents finish startup first
        asyncio.create_task(self._delayed_initial_scan())

    async def _delayed_initial_scan(self) -> None:
        import asyncio, uuid
        await asyncio.sleep(5)  # wait for all agents to be ready
        await self.scan(round_id=str(uuid.uuid4()))

    async def _delayed_rescan(self) -> None:
        """Wait before rescanning so agents have time to settle after a cycle."""
        import asyncio, uuid
        await asyncio.sleep(120)  # 2 min cooldown between cycles
        logger.info("Research agent: auto-rescanning after completed cycle")
        await self.scan(round_id=str(uuid.uuid4()))

    async def handle_message(self, msg: AgentMessage) -> None:
        # Master sends STATUS_UPDATE with action=scan to trigger a scan
        if (
            msg.message_type == MessageType.STATUS_UPDATE
            and msg.to_agent == "research"
            and msg.payload.get("action") == "scan"
        ):
            import asyncio
            asyncio.create_task(self.scan(round_id=msg.payload.get("round_id")))

        # After every completed execution, wait a bit then rescan
        elif msg.message_type == MessageType.EXECUTION_REPORT and not msg.payload.get("failed"):
            import asyncio
            asyncio.create_task(self._delayed_rescan())

    async def scan(self, round_id: str | None = None) -> None:
        """Main scan loop — called by scheduler or master agent."""
        await self.update_status("thinking", "Scanning markets for opportunities...")
        logger.info("Research agent scanning markets")

        try:
            market_data = await self._gather_market_data()
            opportunities = await self._analyze_with_llm(market_data)

            if not opportunities:
                await self.update_status("idle", "No opportunities found this scan")
                return

            for opp in opportunities:
                from_id = round_id or None
                await self.publish(
                    to_agent="all",
                    message_type=MessageType.OPPORTUNITY,
                    payload={"opportunity": opp},
                    round_id=from_id,
                )
                logger.info("Published opportunity: %s %s on %s", opp.get("direction"), opp.get("market"), opp.get("exchange"))

            await self.update_status("idle", f"Scan complete — {len(opportunities)} opportunities found")

        except Exception as e:
            logger.error("Research scan error: %s", e)
            await self.update_status("error", f"Scan error: {str(e)[:100]}")

    async def _gather_market_data(self) -> dict:
        """Gather data from exchanges. Gracefully returns empty lists if not configured."""
        data: dict = {"polymarket_markets": [], "hyperliquid_markets": [], "demo_mode": False}

        # Polymarket
        if self._polymarket and settings.polymarket_private_key:
            try:
                data["polymarket_markets"] = await self._polymarket.get_active_markets(limit=20)
            except Exception as e:
                logger.warning("Polymarket data fetch failed: %s", e)
        else:
            logger.info("Polymarket not configured — skipping live data")

        # Hyperliquid
        if self._hyperliquid and settings.hyperliquid_private_key:
            try:
                data["hyperliquid_markets"] = await self._hyperliquid.get_market_summary()
            except Exception as e:
                logger.warning("Hyperliquid data fetch failed: %s", e)
        else:
            logger.info("Hyperliquid not configured — skipping live data")

        # If neither exchange is configured, use demo/simulated data so agents still run
        if not data["polymarket_markets"] and not data["hyperliquid_markets"]:
            data["demo_mode"] = True
            data["hyperliquid_markets"] = _DEMO_MARKETS

        return data

    async def _analyze_with_llm(self, market_data: dict) -> list[dict]:
        """Use LLM to identify opportunities from raw market data."""
        demo = market_data.get("demo_mode", False)
        note = "\n⚠️ NOTE: No exchange keys configured — using simulated demo data. Set up API keys for real trading.\n" if demo else ""

        user_prompt = f"""Find quick-flip opportunities in this live Polymarket data:{note}

ACTIVE POLYMARKET MARKETS (sorted by 24h volume):
{json.dumps(market_data.get('polymarket_markets', [])[:15], indent=2, default=str)}

Focus ONLY on markets resolving within 72 hours that are mispriced.
Include the condition_id as market_id in your output.
Output a JSON array of up to 3 opportunities."""

        if not settings.openrouter_api_key:
            logger.info("No OPENROUTER_API_KEY — skipping LLM analysis, returning demo opportunity")
            return [_DEMO_OPPORTUNITY] if market_data.get("demo_mode") else []

        try:
            response = await self.call_llm(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.3,
                max_tokens=1500,
            )
            text = response.strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.error("LLM analysis failed: %s", e)

        return []


# ── Demo/fallback data when no exchange keys are configured ────────────────

_DEMO_MARKETS = [
    {"name": "BTC", "mark_price": 65000.0, "funding": 0.0001, "open_interest": 500000000.0, "day_change_pct": 2.3},
    {"name": "ETH", "mark_price": 3200.0, "funding": 0.00008, "open_interest": 200000000.0, "day_change_pct": 1.8},
    {"name": "SOL", "mark_price": 145.0, "funding": 0.00015, "open_interest": 80000000.0, "day_change_pct": -0.5},
]

_DEMO_OPPORTUNITY = {
    "exchange": "hyperliquid",
    "market": "BTC",
    "direction": "long",
    "current_price": 65000.0,
    "target_price": 68000.0,
    "confidence": 0.62,
    "rationale": "DEMO MODE — No real API keys configured. This is a simulated opportunity for testing.",
    "time_horizon": "1d",
    "market_id": "demo",
}
