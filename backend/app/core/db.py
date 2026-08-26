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
                "user_id",
                "ALTER TABLE plans ADD COLUMN user_id VARCHAR(64) DEFAULT 'default'",
            ),
            (
                "plans",
                "history_note",
                "ALTER TABLE plans ADD COLUMN history_note VARCHAR(256)",
            ),
            ("favorite_spots", "lat", "ALTER TABLE favorite_spots ADD COLUMN lat FLOAT"),
            ("favorite_spots", "lon", "ALTER TABLE favorite_spots ADD COLUMN lon FLOAT"),
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


def _sqlite_path() -> Path | None:
    """返回 SQLite 数据库文件路径；非 SQLite 返回 None。"""
    url = settings.database_url
    if not url.startswith("sqlite:///"):
        return None
    return Path(url[len("sqlite:///"):])


def backup_database() -> bool:
    """把 SQLite 数据库备份到对象存储（未配置 S3 时退化为本地 /tmp 副本）。"""
    path = _sqlite_path()
    if path is None or not path.exists():
        return False
    from . import backup as backup_mod
    return backup_mod.backup_db(path)


def restore_database() -> bool:
    """启动时若本地库缺失、云端有备份，下载恢复。"""
    path = _sqlite_path()
    if path is None or path.exists():
        return False
    from . import backup as backup_mod
    return backup_mod.restore_db(path)


def start_backup_loop():
    """启动后台备份线程（预留实例常驻时生效）。"""
    from . import backup as backup_mod
    return backup_mod.start_backup_loop()
