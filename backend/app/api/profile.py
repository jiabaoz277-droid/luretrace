"""装备偏好接口（FR-06）。"""
from __future__ import annotations

from fastapi import APIRouter

from ..core import db
from ..schemas.profile import ProfileData
from ..services import profile as profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_profile():
    with db.get_session() as s:
        return profile_service.get_profile(s).model_dump()


@router.put("")
def put_profile(data: ProfileData):
    with db.get_session() as s:
        return profile_service.save_profile(s, data).model_dump()
