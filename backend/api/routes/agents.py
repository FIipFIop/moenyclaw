from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.agent import Agent
from models.message import AgentMessage

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.name))
    agents = result.scalars().all()
    return [
        {
            "name": a.name,
            "model": a.model,
            "status": a.status,
            "last_message": a.last_message,
            "last_active": a.last_active,
        }
        for a in agents
    ]


@router.get("/{name}/messages")
async def agent_messages(
    name: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentMessage)
        .where((AgentMessage.from_agent == name) | (AgentMessage.to_agent == name))
        .order_by(AgentMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    msgs = result.scalars().all()
    return [
        {
            "id": m.msg_id,
            "round_id": m.round_id,
            "from_agent": m.from_agent,
            "to_agent": m.to_agent,
            "message_type": m.message_type,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in msgs
    ]
