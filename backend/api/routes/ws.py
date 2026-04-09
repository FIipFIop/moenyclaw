import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from core.database import AsyncSessionLocal
from core.websocket_manager import ws_manager
from models.message import AgentMessage

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        # Send replay of last 50 messages on connect
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentMessage).order_by(AgentMessage.created_at.desc()).limit(50)
            )
            msgs = result.scalars().all()

        replay = [
            {
                "event": "agent_message",
                "data": {
                    "id": m.msg_id,
                    "round_id": m.round_id,
                    "from_agent": m.from_agent,
                    "to_agent": m.to_agent,
                    "message_type": m.message_type,
                    "payload": json.loads(m.content) if m.content else {},
                    "timestamp": m.created_at.isoformat() if m.created_at else None,
                },
            }
            for m in reversed(msgs)
        ]
        await ws.send_text(json.dumps({"event": "replay", "data": replay}, default=str))

        # Keep connection alive — just listen (clients are read-only)
        while True:
            await ws.receive_text()  # heartbeat / ping from client

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        await ws_manager.disconnect(ws)
