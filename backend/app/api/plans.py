"""方案卡接口：查询历史方案（保存由对话流程内部完成）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..core import db
from ..core.auth import current_user_id
from ..models.plan import Plan

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/{plan_id}")
def get_plan(plan_id: int, request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        plan = s.get(Plan, plan_id)
        if not plan or plan.user_id != user_id:
            raise HTTPException(status_code=404, detail="方案不存在")
        return plan.to_plan_data()


@router.get("")
def list_plans(request: Request, session_id: str = Query(...)):
    user_id = current_user_id(request)
    with db.get_session() as s:
        plans = (
            s.query(Plan)
            .filter(Plan.session_id == session_id, Plan.user_id == user_id)
            .order_by(Plan.version.desc())
            .all()
        )
        return [p.to_plan_data() for p in plans]
