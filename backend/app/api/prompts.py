"""提示词管理后台接口（X-Admin-Token 鉴权，与业务登录隔离）。"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..core.config import settings
from ..services import prompts

router = APIRouter(prefix="/admin/prompts", tags=["admin"])
ADMIN_COOKIE = "lure_admin_session"


def _require_admin(request: Request, x_admin_token: str | None) -> None:
    if not settings.admin_token:
        raise HTTPException(
            status_code=503,
            detail={"code": "not_configured", "message": "未配置 ADMIN_TOKEN，后台暂不可用"},
        )
    token = x_admin_token or request.cookies.get(ADMIN_COOKIE)
    if not token or not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_admin_token", "message": "管理员令牌不正确"},
        )


class PromptUpdate(BaseModel):
    value: str = Field(..., max_length=20000)


class AdminLogin(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)


@router.post("/login")
def admin_login(body: AdminLogin, response: Response):
    if not settings.admin_token or not secrets.compare_digest(body.token, settings.admin_token):
        raise HTTPException(status_code=401, detail={"code": "invalid_admin_token", "message": "管理员令牌不正确"})
    response.set_cookie(
        ADMIN_COOKIE, settings.admin_token, httponly=True, secure=settings.is_prod,
        samesite="strict", path="/api/v1/admin/prompts", max_age=3600,
    )
    return {"ok": True}


@router.post("/logout", status_code=204)
def admin_logout(response: Response):
    response.delete_cookie(ADMIN_COOKIE, path="/api/v1/admin/prompts", samesite="strict")


@router.get("")
def list_prompts(request: Request, x_admin_token: str | None = Header(None)):
    _require_admin(request, x_admin_token)
    return {"items": prompts.all_prompts()}


@router.get("/{key}")
def get_prompt(key: str, request: Request, x_admin_token: str | None = Header(None)):
    _require_admin(request, x_admin_token)
    if key not in prompts.DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "提示词不存在"})
    meta = prompts.DEFAULT_PROMPTS[key]
    return {
        "key": key,
        "title": meta["title"],
        "description": meta["description"],
        "category": meta["category"],
        "kind": meta["kind"],
        "value": prompts.get_text(key),
        "default": meta["default"],
        "is_modified": prompts.get_text(key) != meta["default"],
    }


@router.put("/{key}")
def update_prompt(key: str, body: PromptUpdate, request: Request, x_admin_token: str | None = Header(None)):
    _require_admin(request, x_admin_token)
    if key not in prompts.DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "提示词不存在"})
    prompts.set_text(key, body.value)
    return {"ok": True, "key": key, "value": prompts.get_text(key)}


@router.post("/{key}/reset")
def reset_prompt(key: str, request: Request, x_admin_token: str | None = Header(None)):
    _require_admin(request, x_admin_token)
    if key not in prompts.DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "提示词不存在"})
    prompts.reset_text(key)
    return {"ok": True, "key": key, "value": prompts.get_text(key)}
