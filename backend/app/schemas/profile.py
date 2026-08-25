"""装备偏好结构（FR-06）。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProfileData(BaseModel):
    rods: list[str] = Field(default_factory=list)
    reels: list[str] = Field(default_factory=list)
    lines: list[str] = Field(default_factory=list)
    lures: list[str] = Field(default_factory=list)
    avoid_methods: list[str] = Field(default_factory=list)
    max_travel_radius: Optional[str] = None
    night_fishing: bool = False
    wading: bool = False
    home_location: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)
