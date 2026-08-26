"""个性化经验统计接口（第 3 阶段，按用户隔离）。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..core import db
from ..core.auth import current_user_id
from ..services import insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("")
def get_insights(request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        return insights.compute(s, user_id)
