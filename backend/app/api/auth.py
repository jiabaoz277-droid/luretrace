"""登录接口：邀请码换短期 token。"""
from __future__ import annotations

import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..core import auth
from ..core import rate_limit
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)


def _client_ip(request: Request) -> str:
    """取网关追加在 XFF 最右侧的地址，不信任客户端可伪造的 X-Real-IP。"""
    candidates = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",")]
    if request.client:
        candidates.append(request.client.host)
    for value in reversed(candidates):
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            continue
    return "unknown"


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response):
    """邀请码正确则写入 HttpOnly Cookie；响应体不再暴露 token。"""
    client_ip = _client_ip(request)
    wait = rate_limit.retry_after(client_ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail={"code": "too_many_attempts", "message": "尝试次数过多，请稍后重试"},
            headers={"Retry-After": str(wait)},
        )
    user_id = auth.verify_invite(body.code)
    if not user_id:
        wait = rate_limit.record_failure(client_ip)
        headers = {"Retry-After": str(wait)} if wait else None
        raise HTTPException(
            status_code=429 if wait else 401,
            detail={
                "code": "too_many_attempts" if wait else "invalid_invite",
                "message": "尝试次数过多，请稍后重试" if wait else "邀请码不正确",
            },
            headers=headers,
        )
    if not settings.token_secret:
        raise HTTPException(
            status_code=503,
            detail={"code": "not_configured", "message": "登录服务未配置 TOKEN_SECRET"},
        )
    rate_limit.record_success(client_ip)
    response.set_cookie(
        key=auth.SESSION_COOKIE,
        value=auth.create_token(user_id),
        max_age=settings.token_ttl_seconds,
        httponly=True,
        secure=settings.is_prod,
        samesite="strict",
        path="/",
    )
    return {
        "ok": True,
        "user_id": user_id,
        "expires_in": settings.token_ttl_seconds,
    }


@router.get("/session")
def session(user_id: str = Depends(auth.get_current_user)):
    return {"authenticated": True, "user_id": user_id}


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(auth.SESSION_COOKIE, path="/", samesite="strict")
