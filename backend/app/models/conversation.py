"""可恢复的对话会话状态。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .plan import Base, utcnow


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_conversation_user_session"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str | None] = mapped_column(String(24), nullable=True)
    pending: Mapped[dict] = mapped_column(JSON, default=dict)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True
    )
