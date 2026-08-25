"""FastAPI 入口：挂载路由、CORS、初始化数据库、健康检查。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, plans
from .core import db
from .core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="路亚问问 MVP", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(plans.router, prefix=settings.api_prefix)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "fishing-assistant", "version": "0.1.0"}
