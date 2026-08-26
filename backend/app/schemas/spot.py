"""收藏钓点结构。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SpotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    location: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
