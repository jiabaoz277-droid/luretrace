"""SQLAlchemy 数据模型：方案卡（版本化）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    time_window: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_species: Mapped[str | None] = mapped_column(String(64), nullable=True)
    travel_radius: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conclusion: Mapped[str] = mapped_column(String(16), default="conditional")
    confidence: Mapped[str] = mapped_column(String(16), default="mid")
    score: Mapped[int] = mapped_column(Integer, default=0)
    best_window: Mapped[str | None] = mapped_column(String(128), nullable=True)
    backup_window: Mapped[str | None] = mapped_column(String(128), nullable=True)
    factors: Mapped[list] = mapped_column(JSON, default=list)
    plan_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    safety: Mapped[list] = mapped_column(JSON, default=list)
    data_basis: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/outdated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def to_plan_data(self) -> dict:
        """转回 Pydantic 可用的字典（避免直接暴露 ORM 对象）。"""
        return {
            "session_id": self.session_id,
            "version": self.version,
            "location": self.location,
            "time_window": self.time_window,
            "target_species": self.target_species,
            "travel_radius": self.travel_radius,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "score": self.score,
            "best_window": self.best_window,
            "backup_window": self.backup_window,
            "factors": json.loads(json.dumps(self.factors or [])),
            "plan_detail": json.loads(json.dumps(self.plan_detail or {})),
            "risks": json.loads(json.dumps(self.risks or [])),
            "safety": json.loads(json.dumps(self.safety or [])),
            "data_basis": json.loads(json.dumps(self.data_basis or {})),
        }
