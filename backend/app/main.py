"""FastAPI 入口：挂载路由、CORS、鉴权、trace_id、初始化/恢复数据库、后台备份。"""
from __future__ import annotations

import uuid
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text

from .api import (
    auth,
    chat,
    dashboard,
    geo,
    insights,
    plans,
    profile,
    prompts,
    reports,
    spots,
)
from .core import db
from .core.auth import get_current_user
from .core.config import settings
from .services import llm

logger = logging.getLogger(__name__)

# 错误监控（可选）：配置 SENTRY_DSN 后自动捕获未处理异常
if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.env,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Sentry initialization failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.restore_database()  # 本地库缺失时先从备份恢复
    db.init_db()
    db.start_backup_loop()  # 预留实例常驻 + 定期备份
    try:
        yield
    finally:
        db.backup_database()  # 正常下线前再做一次快照


app = FastAPI(
    title="路迹 MVP",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.expose_api_docs else None,
    redoc_url="/redoc" if settings.expose_api_docs else None,
    openapi_url="/openapi.json" if settings.expose_api_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*.apigateway-cn-beijing.volceapi.com", "localhost", "127.0.0.1", "testserver"],
)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    """为每个请求生成/透传 trace_id，串联排错。"""
    supplied = request.headers.get("X-Trace-Id", "")
    trace_id = supplied if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied) else uuid.uuid4().hex[:16]
    request.state.trace_id = trace_id
    if settings.is_prod and request.headers.get("x-forwarded-proto", "").lower() == "http":
        response = RedirectResponse(str(request.url.replace(scheme="https")), status_code=308)
    else:
        response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
    if request.url.path.startswith("/admin"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'none'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response


# 登录接口（无需鉴权）
app.include_router(auth.router, prefix=settings.api_prefix)

# 提示词管理后台（X-Admin-Token 鉴权，与业务登录隔离）
app.include_router(prompts.router, prefix=settings.api_prefix)

# 其余业务接口：统一要求登录（无 token 访问被拒）
_protected_routers = [
    chat.router,
    plans.router,
    profile.router,
    reports.router,
    spots.router,
    insights.router,
    dashboard.router,
    geo.router,
]
for _router in _protected_routers:
    app.include_router(
        _router, prefix=settings.api_prefix, dependencies=[Depends(get_current_user)]
    )


@app.get("/api/v1/health")
def health():
    try:
        with db.get_session() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


_ADMIN_HTML = Path(__file__).resolve().parent / "admin" / "index.html"


@app.get("/admin", include_in_schema=False)
@app.get("/admin/prompts", include_in_schema=False)
def admin_ui():
    return FileResponse(_ADMIN_HTML)


@app.get("/api/v1/model/status")
def model_status():
    """模型接入状态（不暴露密钥）。"""
    if not settings.expose_model_status:
        raise HTTPException(status_code=404, detail="Not Found")
    return {
        "configured": llm.is_configured(),
        "model": settings.model_name or "deepseek-chat",
        "base_url": settings.model_base_url or "https://api.deepseek.com",
    }
