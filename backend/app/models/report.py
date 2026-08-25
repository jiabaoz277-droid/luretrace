"""战报记录：模型推断与用户输入分字段保存，复盘需确认后写入。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .plan import Base, utcnow

# 四类结果（PRD FR-07）
RESULT_TYPES = ("landed", "bite_no_fish", "skunked", "no_go")
RESULT_LABELS = {
    "landed": "上鱼",
    "bite_no_fish": "有口未中",
    "skunked": "空军",
    "no_go": "未出钓",
}


class CatchReport(Base):
    __tablename__ = "catch_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_type: Mapped[str] = mapped_column(String(24), default="skunked")
    # 用户可选补充字段
    species: Mapped[str | None] = mapped_column(String(64), nullable=True)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    length_weight: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lure: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actual_window: Mapped[str | None] = mapped_column(String(64), nullable=True)
    water_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    flow: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 复盘：模型生成 + 用户确认后才视为已写入长期历史
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    # 模型推断 vs 用户明确输入（FR-07 分字段）
    inferred: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "result_type": self.result_type,
            "result_label": RESULT_LABELS.get(self.result_type, self.result_type),
            "species": self.species,
            "count": self.count,
            "length_weight": self.length_weight,
            "lure": self.lure,
            "actual_window": self.actual_window,
            "water_color": self.water_color,
            "flow": self.flow,
            "note": self.note,
            "review": self.review,
            "review_confirmed": self.review_confirmed,
            "inferred": self.inferred or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
