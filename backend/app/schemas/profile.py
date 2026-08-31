"""装备偏好结构（FR-06）。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProfileData(BaseModel):
    rods: list[str] = Field(default_factory=list, max_length=50)
    reels: list[str] = Field(default_factory=list, max_length=50)
    lines: list[str] = Field(default_factory=list, max_length=50)
    lures: list[str] = Field(default_factory=list, max_length=50)
    avoid_methods: list[str] = Field(default_factory=list, max_length=50)
    max_travel_radius: Optional[str] = Field(None, max_length=64)
    night_fishing: bool = False
    wading: bool = False
    home_location: Optional[str] = Field(None, max_length=128)
    constraints: list[str] = Field(default_factory=list, max_length=50)
