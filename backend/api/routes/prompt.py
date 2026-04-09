from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.message_bus import AgentMessage, MessageType, bus

router = APIRouter(prefix="/api/prompt", tags=["prompt"])


class PromptRequest(BaseModel):
    message: str


@router.post("")
async def send_prompt(body: PromptRequest, request: Request):
    """Send a user prompt to the master agent."""
    text = body.message.strip()
    if not text:
        return {"status": "ignored"}

    msg = AgentMessage(
        from_agent="user",
        to_agent="master",
        message_type=MessageType.USER_PROMPT,
        payload={"text": text},
    )
    await bus.publish(msg)
    return {"status": "sent", "id": msg.id}
