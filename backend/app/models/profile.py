"""用户装备与偏好（单用户 MVP，user_id="default"）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .plan import Base, utcnow


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, default="default")
    rods: Mapped[list] = mapped_column(JSON, default=list)
    reels: Mapped[list] = mapped_column(JSON, default=list)
    lines: Mapped[list] = mapped_column(JSON, default=list)
    lures: Mapped[list] = mapped_column(JSON, default=list)
    avoid_methods: Mapped[list] = mapped_column(JSON, default=list)
    max_travel_radius: Mapped[str | None] = mapped_column(String(32), nullable=True)
    night_fishing: Mapped[bool] = mapped_column(Boolean, default=False)
    wading: Mapped[bool] = mapped_column(Boolean, default=False)
    home_location: Mapped[str | None] = mapped_column(String(64), nullable=True)
    constraints: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "rods": self.rods or [],
            "reels": self.reels or [],
            "lines": self.lines or [],
            "lures": self.lures or [],
            "avoid_methods": self.avoid_methods or [],
            "max_travel_radius": self.max_travel_radius,
            "night_fishing": self.night_fishing,
            "wading": self.wading,
            "home_location": self.home_location,
            "constraints": self.constraints or [],
        }
