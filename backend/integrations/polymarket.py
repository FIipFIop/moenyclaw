"""
Polymarket integration.
Uses the CLOB API for market data and order placement.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

CLOB_BASE = "https://clob.polymarket.com"
GAMMA_BASE = "https://gamma-api.polymarket.com"


class PolymarketClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._clob_client = None
        self._ready = False

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _init_clob(self) -> None:
        if self._ready:
            return
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds

            creds = ApiCreds(
                api_key=settings.polymarket_api_key,
                api_secret="",
                api_passphrase="",
            )
            self._clob_client = ClobClient(
                host=CLOB_BASE,
                key=settings.polymarket_private_key,
                chain_id=137,  # Polygon
                creds=creds,
                signature_type=1 if settings.polymarket_proxy_address else 0,
                funder=settings.polymarket_proxy_address or None,
            )
            self._ready = True
            logger.info("Polymarket CLOB client initialized")
        except Exception as e:
            logger.warning("Polymarket CLOB init failed (no API key?): %s", e)
            self._ready = False

    async def get_active_markets(self, limit: int = 30) -> list[dict]:
        """Fetch active markets sorted by 24h volume. Includes end_date for time-to-resolve filtering."""
        try:
            client = await self._get_http_client()
            resp = await client.get(
                f"{GAMMA_BASE}/markets",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": limit,
                    "order": "volume24hr",
                    "ascending": "false",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            markets = []
            for m in data:
                try:
                    prices = [float(p) for p in (m.get("outcomePrices") or [])]
                except Exception:
                    prices = []
                markets.append({
                    "condition_id": m.get("conditionId"),
                    "question": m.get("question"),
                    "end_date": m.get("endDate"),
                    "volume_24hr": round(float(m.get("volume24hr") or 0), 0),
                    "volume_total": round(float(m.get("volume") or 0), 0),
                    "liquidity": round(float(m.get("liquidity") or 0), 0),
                    "outcomes": m.get("outcomes", []),
                    "outcome_prices": prices,  # [yes_price, no_price]
                    "yes_price": prices[0] if prices else None,
                    "no_price": prices[1] if len(prices) > 1 else None,
                })
            return markets

        except Exception as e:
            logger.error("Polymarket get_active_markets error: %s", e)
            return []

    async def get_orderbook(self, token_id: str) -> dict:
        """Get order book for a specific market token."""
        try:
            client = await self._get_http_client()
            resp = await client.get(f"{CLOB_BASE}/book", params={"token_id": token_id})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Polymarket get_orderbook error: %s", e)
            return {}

    async def get_balance(self) -> float:
        """Get USDC balance from Polymarket wallet."""
        try:
            self._init_clob()
            if not self._ready or not self._clob_client:
                return 0.0
            balance_data = self._clob_client.get_balance()
            return float(balance_data) / 1e6  # USDC has 6 decimals
        except Exception as e:
            logger.error("Polymarket get_balance error: %s", e)
            return 0.0

    async def place_order(
        self,
        market_id: str,
        is_yes: bool,
        size_pct: float,
        price: float | None = None,
    ) -> dict[str, Any]:
        """Place a buy order on Polymarket."""
        if not settings.trading_enabled:
            return {"status": "dry_run", "message": "Trading disabled"}

        try:
            self._init_clob()
            if not self._ready or not self._clob_client:
                return {"status": "failed", "error": "CLOB client not initialized"}

            from py_clob_client.clob_types import BuyMarketOrder, OrderArgs, OrderType

            # Get market details to find token_id
            client = await self._get_http_client()
            resp = await client.get(f"{GAMMA_BASE}/markets/{market_id}")
            market = resp.json()

            tokens = market.get("tokens", [])
            token = next((t for t in tokens if (t.get("outcome") == "Yes") == is_yes), None)
            if not token:
                return {"status": "failed", "error": "Market token not found"}

            token_id = token.get("token_id")

            order_args = OrderArgs(
                token_id=token_id,
                price=price or 0.5,
                size=size_pct * 10,  # approximate USD amount
                side="buy",
            )
            result = self._clob_client.create_and_post_order(order_args)

            return {
                "status": "open" if result.get("orderID") else "failed",
                "order_id": result.get("orderID"),
                "raw": result,
            }

        except Exception as e:
            logger.error("Polymarket place_order error: %s", e)
            return {"status": "failed", "error": str(e)}

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


polymarket_client = PolymarketClient()
