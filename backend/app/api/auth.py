"""登录接口：邀请码换短期 token。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core import auth
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)


@router.post("/login")
def login(body: LoginRequest):
    """邀请码正确则返回 token；错误返回 401。"""
    user_id = auth.verify_invite(body.code)
    if not user_id:
        raise HTTPException(
            status_code=401, detail={"code": "invalid_invite", "message": "邀请码不正确"}
        )
    if not settings.token_secret:
        raise HTTPException(
            status_code=503,
            detail={"code": "not_configured", "message": "登录服务未配置 TOKEN_SECRET"},
        )
    return {
        "token": auth.create_token(user_id),
        "user_id": user_id,
        "expires_in": settings.token_ttl_seconds,
    }
