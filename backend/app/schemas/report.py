"""战报结构（FR-07）。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ResultType = Literal["landed", "bite_no_fish", "skunked", "no_go"]


class ReportCreate(BaseModel):
    session_id: str = Field(min_length=1)
    plan_id: Optional[int] = None
    result_type: ResultType = "skunked"
    species: Optional[str] = None
    count: Optional[int] = Field(default=None, ge=0)
    length_weight: Optional[str] = None
    lure: Optional[str] = None
    actual_window: Optional[str] = None
    water_color: Optional[str] = None
    flow: Optional[str] = None
    note: Optional[str] = None


class ReviewConfirm(BaseModel):
    confirmed: bool = True
