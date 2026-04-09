from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    msg_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)  # uuid4
    round_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # groups one trade cycle
    from_agent: Mapped[str] = mapped_column(String(50), nullable=False)
    to_agent: Mapped[str] = mapped_column(String(50), nullable=False)  # agent name or "all"
    message_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    reply_to: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
