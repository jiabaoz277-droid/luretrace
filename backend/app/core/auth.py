"""邀请码登录 + 无状态 token 鉴权。

- 邀请码映射到稳定的 user_id（邀请码的哈希前缀），一个码 = 一个独立用户身份。
- token 为 HMAC 签名（user_id + 过期时间），校验时不查库、无状态、可水平扩展。
- 签名密钥来自 TOKEN_SECRET 环境变量，永不落库、不回显。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from fastapi import Header, HTTPException, Request

from .config import settings

SESSION_COOKIE = "lure_session"


def _user_id_for_code(code: str) -> str:
    """把邀请码映射为稳定、不暴露原始码的用户标识。"""
    digest = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()
    return "u-" + digest[:16]


def verify_invite(code: str) -> str | None:
    """校验邀请码，命中返回 user_id，否则 None。"""
    if not code:
        return None
    for valid in settings.invite_codes:
        if valid and secrets.compare_digest(code.strip(), valid.strip()):
            return _user_id_for_code(valid)
    return None


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(payload: str) -> str:
    if not settings.token_secret:
        raise RuntimeError("未配置 TOKEN_SECRET，无法签发登录 token")
    return hmac.new(
        settings.token_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def create_token(user_id: str) -> str:
    """签发 token：user_id.expiry.signature（urlsafe base64 + HMAC）。"""
    exp = int(time.time()) + settings.token_ttl_seconds
    payload = _b64(user_id.encode("utf-8")) + "." + _b64(str(exp).encode("ascii"))
    return payload + "." + _sign(payload)


def resolve_token(token: str) -> str | None:
    """校验 token，合法返回 user_id，否则 None。"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[0] + "." + parts[1]
        if not secrets.compare_digest(parts[2], _sign(payload)):
            return None
        user_id = _unb64(parts[0]).decode("utf-8")
        exp = int(_unb64(parts[1]).decode("ascii"))
        if exp < int(time.time()):
            return None
        return user_id
    except Exception:  # noqa: BLE001
        return None


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_current_user(request: Request, authorization: str | None = Header(None)) -> str:
    """校验 HttpOnly 会话 Cookie；保留 Bearer 兼容已有 API 客户端。"""
    token = _extract_bearer(authorization) or request.cookies.get(SESSION_COOKIE, "")
    user_id = resolve_token(token)
    if not user_id:
        raise HTTPException(
            status_code=401, detail={"code": "unauthorized", "message": "请先登录"}
        )
    request.state.user_id = user_id
    return user_id


def current_user_id(request: Request) -> str:
    """从 request.state 读取已鉴权的 user_id（由 get_current_user 写入）。"""
    return getattr(request.state, "user_id", "default")
