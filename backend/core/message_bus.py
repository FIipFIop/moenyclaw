"""
Central async message bus for agent communication.

All agents publish messages here. The dispatcher routes them to
registered handler coroutines and fans out to WebSocket clients.
All messages are persisted to the agent_messages table.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str  # agent name or "all"
    message_type: str  # see MessageType constants below
    payload: dict[str, Any]
    round_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reply_to: str | None = None
    priority: int = 3  # 1=low … 5=high

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "round_id": self.round_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
        }


class MessageType:
    OPPORTUNITY = "OPPORTUNITY"
    ANALYSIS = "ANALYSIS"
    RISK_REVIEW = "RISK_REVIEW"
    DEBATE_CHALLENGE = "DEBATE_CHALLENGE"
    MASTER_DECISION = "MASTER_DECISION"
    EXECUTION_REPORT = "EXECUTION_REPORT"
    SELF_CORRECTION = "SELF_CORRECTION"
    STATUS_UPDATE = "STATUS_UPDATE"
    HOURLY_REPORT = "HOURLY_REPORT"
    USER_PROMPT = "USER_PROMPT"


HandlerFn = Callable[[AgentMessage], Coroutine[Any, Any, None]]


class MessageBus:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._handlers: dict[str, list[HandlerFn]] = {}
        self._running = False
        self._ws_manager = None  # injected after init to avoid circular imports
        self._db_session_factory = None  # injected at startup

    def set_ws_manager(self, manager: Any) -> None:
        self._ws_manager = manager

    def set_session_factory(self, factory: Any) -> None:
        self._db_session_factory = factory

    def subscribe(self, agent_name: str, handler: HandlerFn) -> None:
        self._handlers.setdefault(agent_name, []).append(handler)
        self._handlers.setdefault("all", [])  # ensure "all" key exists

    async def publish(self, msg: AgentMessage) -> None:
        await self._queue.put(msg)

    async def _persist(self, msg: AgentMessage) -> None:
        if not self._db_session_factory:
            return
        try:
            from models.message import AgentMessage as AgentMessageModel

            async with self._db_session_factory() as session:
                record = AgentMessageModel(
                    msg_id=msg.id,
                    round_id=msg.round_id,
                    from_agent=msg.from_agent,
                    to_agent=msg.to_agent,
                    message_type=msg.message_type,
                    content=json.dumps(msg.payload, default=str),
                    reply_to=msg.reply_to,
                    created_at=msg.timestamp,
                )
                session.add(record)
                await session.commit()
        except Exception as e:
            logger.error("Failed to persist message: %s", e)

    async def _dispatch(self, msg: AgentMessage) -> None:
        # Persist to DB
        await self._persist(msg)

        # Fan out to WebSocket clients
        if self._ws_manager:
            await self._ws_manager.broadcast({"event": "agent_message", "data": msg.to_dict()})

        # Route to handlers
        targets: list[HandlerFn] = []

        # Broadcast to everyone registered under "all"
        for handler in self._handlers.get("all", []):
            targets.append(handler)

        # Also route to specific target (avoid double-delivery for "all" messages)
        if msg.to_agent != "all":
            for handler in self._handlers.get(msg.to_agent, []):
                if handler not in targets:
                    targets.append(handler)

        for handler in targets:
            try:
                await handler(msg)
            except Exception as e:
                logger.error("Handler error for %s → %s: %s", msg.from_agent, msg.to_agent, e)

    async def run(self) -> None:
        self._running = True
        logger.info("MessageBus dispatcher started")
        while self._running:
            try:
                msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                asyncio.create_task(self._dispatch(msg))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("MessageBus dispatch error: %s", e)

    def stop(self) -> None:
        self._running = False


bus = MessageBus()
