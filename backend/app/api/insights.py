"""个性化经验统计接口（第 3 阶段）。"""
from __future__ import annotations

from fastapi import APIRouter

from ..core import db
from ..services import insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("")
def get_insights():
    with db.get_session() as s:
        return insights.compute(s)
