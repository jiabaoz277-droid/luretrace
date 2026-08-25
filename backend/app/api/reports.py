"""战报接口（FR-07）：列表 / 确认复盘 / 删除。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..core import db
from ..models.report import CatchReport
from ..schemas.report import ReviewConfirm

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports(session_id: str = Query(...)):
    with db.get_session() as s:
        reps = (
            s.query(CatchReport)
            .filter(CatchReport.session_id == session_id)
            .order_by(CatchReport.id.desc())
            .all()
        )
        return [r.to_dict() for r in reps]


@router.get("/{report_id}")
def get_report(report_id: int):
    with db.get_session() as s:
        r = s.get(CatchReport, report_id)
        if not r:
            raise HTTPException(status_code=404, detail="战报不存在")
        return r.to_dict()


@router.post("/{report_id}/review")
def confirm_review(report_id: int, body: ReviewConfirm):
    with db.get_session() as s:
        r = s.get(CatchReport, report_id)
        if not r:
            raise HTTPException(status_code=404, detail="战报不存在")
        r.review_confirmed = body.confirmed
        s.commit()
        s.refresh(r)
        return r.to_dict()


@router.delete("/{report_id}")
def delete_report(report_id: int):
    with db.get_session() as s:
        r = s.get(CatchReport, report_id)
        if not r:
            raise HTTPException(status_code=404, detail="战报不存在")
        s.delete(r)
        s.commit()
        return {"deleted": report_id}
