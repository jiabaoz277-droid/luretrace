"""FastAPI 入口：挂载路由、CORS、鉴权、trace_id、初始化/恢复数据库、后台备份。"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    auth,
    chat,
    dashboard,
    geo,
    insights,
    plans,
    profile,
    reports,
    spots,
)
from .core import db
from .core.auth import get_current_user
from .core.config import settings
from .services import llm

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
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.restore_database()  # 本地库缺失时先从备份恢复
    db.init_db()
    db.start_backup_loop()  # 预留实例常驻 + 定期备份
    yield


app = FastAPI(title="路亚问问 MVP", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    """为每个请求生成/透传 trace_id，串联排错。"""
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:16]
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


# 登录接口（无需鉴权）
app.include_router(auth.router, prefix=settings.api_prefix)

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
    return {"status": "ok", "service": "fishing-assistant", "version": "0.1.0"}


@app.get("/api/v1/model/status")
def model_status():
    """模型接入状态（不暴露密钥）。"""
    return {
        "configured": llm.is_configured(),
        "model": settings.model_name or "deepseek-chat",
        "base_url": settings.model_base_url or "https://api.deepseek.com",
    }
