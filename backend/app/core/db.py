"""数据库引擎与会话工厂（SQLite + SQLAlchemy 同步）。"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from .config import settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db() -> None:
    from ..models import Base

    url = settings.database_url
    if url.startswith("sqlite:///"):
        db_path = Path(url[len("sqlite:///"):])
        db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=get_engine())
    _migrate_legacy()


def _migrate_legacy() -> None:
    """轻量迁移：为旧库补充新增列（Alembic 引入前的过渡方案）。"""
    engine = get_engine()
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, col, ddl in [
            (
                "catch_reports",
                "user_id",
                "ALTER TABLE catch_reports ADD COLUMN user_id VARCHAR(64) DEFAULT 'default'",
            ),
            (
                "plans",
                "history_note",
                "ALTER TABLE plans ADD COLUMN history_note VARCHAR(256)",
            ),
        ]:
            try:
                cols = {c["name"] for c in insp.get_columns(table)}
            except Exception:  # 表不存在
                continue
            if col not in cols:
                conn.execute(text(ddl))


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False)
    return _SessionLocal()
