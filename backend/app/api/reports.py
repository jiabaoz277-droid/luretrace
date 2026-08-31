"""战报接口（FR-07）：列表 / 详情 / 确认复盘 / 删除（按用户隔离）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..core import db
from ..core.auth import current_user_id
from ..models.report import CatchReport
from ..schemas.report import ReviewConfirm

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_owned(s, user_id: str, report_id: int) -> CatchReport:
    r = s.get(CatchReport, report_id)
    if not r or r.user_id != user_id:
        raise HTTPException(status_code=404, detail="战报不存在")
    return r


@router.get("")
def list_reports(
    request: Request,
    session_id: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    user_id = current_user_id(request)
    with db.get_session() as s:
        reps = (
            s.query(CatchReport)
            .filter(CatchReport.session_id == session_id, CatchReport.user_id == user_id)
            .order_by(CatchReport.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in reps]


@router.get("/{report_id}")
def get_report(report_id: int, request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        return _get_owned(s, user_id, report_id).to_dict()


@router.post("/{report_id}/review")
def confirm_review(report_id: int, body: ReviewConfirm, request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        r = _get_owned(s, user_id, report_id)
        r.review_confirmed = body.confirmed
        s.commit()
        s.refresh(r)
        return r.to_dict()


@router.delete("/{report_id}")
def delete_report(report_id: int, request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        r = _get_owned(s, user_id, report_id)
        s.delete(r)
        s.commit()
        return {"deleted": report_id}
