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

SYSTEM_PROMPT = """You are a crypto market research agent. Your job is to identify high-probability trading opportunities on Polymarket (prediction markets) and Hyperliquid (perpetuals).

For each opportunity you identify, output a JSON object with:
{
  "exchange": "polymarket" or "hyperliquid",
  "market": "<market name or token>",
  "direction": "buy/long or sell/short",
  "current_price": <float>,
  "target_price": <float>,
  "confidence": <0.0 to 1.0>,
  "rationale": "<brief explanation>",
  "time_horizon": "<e.g. 4h, 1d, 1w>",
  "market_id": "<id if available>"
}

Only output opportunities with confidence >= 0.6. Output an array of JSON objects.
Be concise and data-driven."""


class ResearchAgent(BaseAgent):
    name = "research"
    model = settings.model_research

    def __init__(self, bus: MessageBus) -> None:
        super().__init__(bus)
        self._polymarket = None
        self._hyperliquid = None

    async def startup(self) -> None:
        from integrations.hyperliquid import hyperliquid_client
        from integrations.polymarket import polymarket_client
        self._polymarket = polymarket_client
        self._hyperliquid = hyperliquid_client
        await self.update_status("idle", "Research agent ready — awaiting scan trigger")

    async def handle_message(self, msg: AgentMessage) -> None:
        # Research agent doesn't react to other agents except master triggers
        pass

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
        """Gather data from exchanges."""
        data = {}
        try:
            if self._polymarket:
                markets = await self._polymarket.get_active_markets(limit=20)
                data["polymarket_markets"] = markets
        except Exception as e:
            logger.warning("Polymarket data fetch failed: %s", e)
            data["polymarket_markets"] = []

        try:
            if self._hyperliquid:
                meta = await self._hyperliquid.get_market_summary()
                data["hyperliquid_markets"] = meta
        except Exception as e:
            logger.warning("Hyperliquid data fetch failed: %s", e)
            data["hyperliquid_markets"] = []

        return data

    async def _analyze_with_llm(self, market_data: dict) -> list[dict]:
        """Use LLM to identify opportunities from raw market data."""
        user_prompt = f"""Analyze the following market data and identify trading opportunities:

POLYMARKET (prediction markets):
{json.dumps(market_data.get('polymarket_markets', [])[:10], indent=2, default=str)}

HYPERLIQUID (perpetuals — top movers/volume):
{json.dumps(market_data.get('hyperliquid_markets', [])[:10], indent=2, default=str)}

Identify up to 3 high-confidence opportunities. Output a JSON array."""

        try:
            response = await self.call_llm(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.3,
                max_tokens=1500,
            )
            # Extract JSON from response
            text = response.strip()
            # Find JSON array in response
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.error("LLM analysis failed: %s", e)

        return []
