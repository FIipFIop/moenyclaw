"""
Abstract base class for all agents.

Every agent:
- Has a name and an assigned OpenRouter model
- Subscribes to the message bus
- Can publish messages to the bus
- Can call the LLM via OpenRouter
- Updates its status row in the DB
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from core.config import settings
from core.database import AsyncSessionLocal
from core.message_bus import AgentMessage, MessageBus, MessageType
from integrations.openrouter import openrouter

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str
    model: str

    def __init__(self, bus: MessageBus) -> None:
        self.bus = bus
        # Subscribe to "all" broadcasts AND to own name
        bus.subscribe("all", self._handle_broadcast)
        bus.subscribe(self.name, self._handle_direct)

    # ── Public interface ───────────────────────────────────────────────────

    async def publish(
        self,
        to_agent: str,
        message_type: str,
        payload: dict[str, Any],
        round_id: str | None = None,
        reply_to: str | None = None,
    ) -> AgentMessage:
        msg = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            reply_to=reply_to,
        )
        if round_id:
            msg.round_id = round_id
        await self.bus.publish(msg)
        return msg

    async def call_llm(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        if not settings.openrouter_api_key:
            logger.warning("%s: No OPENROUTER_API_KEY — LLM call skipped", self.name)
            return '{"error": "no_api_key", "message": "Set OPENROUTER_API_KEY to enable AI reasoning"}'
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return await openrouter.chat(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def update_status(self, status: str, last_message: str = "") -> None:
        from core.websocket_manager import ws_manager
        from models.agent import Agent
        from sqlalchemy import select

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Agent).where(Agent.name == self.name))
                agent = result.scalar_one_or_none()
                if agent:
                    agent.status = status
                    agent.last_message = last_message[:500] if last_message else ""
                    agent.last_active = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.error("Failed to update agent status: %s", e)

        # Also broadcast status update to WS clients
        await ws_manager.broadcast({
            "event": "agent_status",
            "data": {
                "name": self.name,
                "status": status,
                "last_message": last_message[:200] if last_message else "",
                "timestamp": datetime.utcnow().isoformat(),
            },
        })

    # ── Internal routing ───────────────────────────────────────────────────

    async def _handle_broadcast(self, msg: AgentMessage) -> None:
        """Called for every 'all' broadcast. Skip own messages."""
        if msg.from_agent == self.name:
            return
        await self.handle_message(msg)

    async def _handle_direct(self, msg: AgentMessage) -> None:
        """Called for messages addressed directly to this agent."""
        await self.handle_message(msg)

    @abstractmethod
    async def handle_message(self, msg: AgentMessage) -> None:
        """Override in each agent to react to incoming messages."""
        ...

    async def startup(self) -> None:
        """Called once after all agents are registered. Override for init work."""
        await self.update_status("idle", "Agent ready")

    async def teardown(self) -> None:
        """Called on shutdown."""
        pass
