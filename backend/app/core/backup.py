"""数据备份：SQLite 文件定期备份到对象存储（S3 兼容协议），启动时恢复。

- 配置 STORAGE_PROVIDER=s3 + S3_* 时上传到 TOS 等 S3 兼容桶；
- 未配置时退化为 /tmp 本地副本（同机备份，作用有限，仅开发兜底）。
"""
from __future__ import annotations

import shutil
import logging
import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

from .config import settings

_BACKUP_KEY = "lure-backup/app.db"
_LOCAL_FALLBACK = Path("/tmp") / "db_backup" / "app.db"
_BACKUP_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def _s3_configured() -> bool:
    return bool(
        settings.storage_provider == "s3"
        and settings.s3_endpoint
        and settings.s3_access_key
        and settings.s3_secret_key
        and settings.s3_bucket
    )


def _s3_client():
    import boto3  # 延迟导入，避免未安装时影响启动
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )


def backup_db(path: Path) -> bool:
    """用 SQLite backup API 生成一致性快照，再上传到对象存储。"""
    if not path.exists() or not _BACKUP_LOCK.acquire(blocking=False):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="lure-db-backup-") as temp_dir:
            snapshot = Path(temp_dir) / "app.db"
            with sqlite3.connect(path, timeout=30) as source:
                with sqlite3.connect(snapshot) as target:
                    source.backup(target)
            if _s3_configured():
                _s3_client().upload_file(str(snapshot), settings.s3_bucket, _BACKUP_KEY)
            else:
                _LOCAL_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(snapshot, _LOCAL_FALLBACK)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Database backup failed")
        return False
    finally:
        _BACKUP_LOCK.release()


def restore_db(path: Path) -> bool:
    """下载后先做完整性检查，再原子替换本地数据库。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".restore.tmp")
        if _s3_configured():
            _s3_client().download_file(settings.s3_bucket, _BACKUP_KEY, str(temp_path))
        else:
            if not _LOCAL_FALLBACK.exists():
                return False
            shutil.copy2(_LOCAL_FALLBACK, temp_path)
        with sqlite3.connect(temp_path) as restored:
            result = restored.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError("restored SQLite database failed integrity_check")
        os.replace(temp_path, path)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Database restore failed")
        return False


def start_backup_loop() -> threading.Thread:
    """后台线程：启动后先备份一次，此后每隔 backup_interval_seconds 备份一次。"""

    def _loop():
        while True:
            try:
                from . import db  # 延迟导入，避免循环依赖
                if not db.backup_database():
                    logger.warning("Scheduled database backup did not complete")
            except Exception:  # noqa: BLE001
                logger.exception("Scheduled database backup crashed")
            time.sleep(settings.backup_interval_seconds)

    t = threading.Thread(target=_loop, daemon=True, name="db-backup")
    t.start()
    return t
