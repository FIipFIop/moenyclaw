"""
OpenRouter API client.
Free-tier models: rate-limited, so we retry with exponential backoff.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MAX_RETRIES = 4
RETRY_BASE_DELAY = 2.0  # seconds


class OpenRouterClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=OPENROUTER_BASE,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/FIipFIop/moenyclaw",
                    "X-Title": "MoneyClaw Agent Network",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
        return self._client

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat request and return the assistant's text response."""
        client = await self._get_client()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.post("/chat/completions", json=payload)

                if resp.status_code == 429:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning("OpenRouter rate limited. Retrying in %.1fs", delay)
                    await asyncio.sleep(delay)
                    continue

                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

            except httpx.HTTPStatusError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.error("OpenRouter HTTP error %s, retry %d/%d", e.response.status_code, attempt + 1, MAX_RETRIES)
                await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))

            except httpx.RequestError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.error("OpenRouter request error: %s, retry %d/%d", e, attempt + 1, MAX_RETRIES)
                await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))

        raise RuntimeError(f"OpenRouter: all {MAX_RETRIES} retries exhausted for model {model}")

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


openrouter = OpenRouterClient()
