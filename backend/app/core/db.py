"""数据库引擎与会话工厂（本地 SQLite，生产可切换托管数据库）。"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .config import settings

_engine = None
_SessionLocal = None
logger = logging.getLogger(__name__)


def get_engine():
    global _engine
    if _engine is None:
        kwargs: dict = {"pool_pre_ping": True}
        if settings.database_url.startswith("sqlite:"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        _engine = create_engine(settings.database_url, **kwargs)
    return _engine


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record) -> None:  # noqa: ARG001
    """SQLite 开启 WAL 和忙等待，减少并发读写时的 database is locked。"""
    if dbapi_connection.__class__.__module__.split(".")[0] != "sqlite3":
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


def init_db() -> None:
    from ..models import Base

    url = settings.database_url
    if url.startswith("sqlite:///"):
        db_path = Path(url[len("sqlite:///"):])
        db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=get_engine())
    _migrate_legacy()
    if settings.is_prod and settings.database_url.startswith("sqlite:"):
        logger.warning(
            "Production is using SQLite. Configure DATABASE_URL with a managed database "
            "before enabling multiple veFaaS instances."
        )


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

        # 旧实现在新任务时会把版本重置为 1，先无损重排历史版本。
        duplicate_groups = conn.execute(
            text(
                "SELECT user_id, session_id FROM plans "
                "GROUP BY user_id, session_id "
                "HAVING COUNT(*) <> COUNT(DISTINCT version)"
            )
        ).mappings().all()
        for group in duplicate_groups:
            rows = conn.execute(
                text(
                    "SELECT id FROM plans "
                    "WHERE user_id = :user_id AND session_id = :session_id "
                    "ORDER BY created_at ASC, id ASC"
                ),
                {"user_id": group["user_id"], "session_id": group["session_id"]},
            ).mappings().all()
            for version, row in enumerate(rows, 1):
                conn.execute(
                    text("UPDATE plans SET version = :version WHERE id = :id"),
                    {"version": version, "id": row["id"]},
                )
            logger.warning(
                "Re-numbered %s legacy plans for session %s",
                len(rows),
                group["session_id"],
            )

        # 旧库 create_all 不会补 UniqueConstraint，修复数据后建立唯一索引。
        try:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_plan_user_session_version "
                    "ON plans (user_id, session_id, version)"
                )
            )
        except Exception:  # 旧数据已有重复时不阻断启动
            logger.exception("Unable to create the plan version uniqueness index")


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
