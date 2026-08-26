"""装备偏好接口（FR-06）。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..core import db
from ..core.auth import current_user_id
from ..schemas.profile import ProfileData
from ..services import profile as profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_profile(request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        return profile_service.get_profile(s, user_id).model_dump()


@router.put("")
def put_profile(data: ProfileData, request: Request):
    user_id = current_user_id(request)
    with db.get_session() as s:
        return profile_service.save_profile(s, data, user_id).model_dump()
