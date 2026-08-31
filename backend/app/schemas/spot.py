"""收藏钓点结构。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SpotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    location: Optional[str] = Field(None, max_length=128)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
