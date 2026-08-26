"""数据备份：SQLite 文件定期备份到对象存储（S3 兼容协议），启动时恢复。

- 配置 STORAGE_PROVIDER=s3 + S3_* 时上传到 TOS 等 S3 兼容桶；
- 未配置时退化为 /tmp 本地副本（同机备份，作用有限，仅开发兜底）。
"""
from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from .config import settings

_BACKUP_KEY = "lure-backup/app.db"
_LOCAL_FALLBACK = Path("/tmp") / "db_backup" / "app.db"


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
    """把 path 上传到对象存储；成功返回 True。"""
    try:
        if _s3_configured():
            _s3_client().upload_file(str(path), settings.s3_bucket, _BACKUP_KEY)
        else:
            _LOCAL_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, _LOCAL_FALLBACK)
        return True
    except Exception:  # noqa: BLE001
        return False


def restore_db(path: Path) -> bool:
    """从对象存储下载备份到 path；成功返回 True。"""
    try:
        if _s3_configured():
            path.parent.mkdir(parents=True, exist_ok=True)
            _s3_client().download_file(settings.s3_bucket, _BACKUP_KEY, str(path))
        else:
            if not _LOCAL_FALLBACK.exists():
                return False
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_LOCAL_FALLBACK, path)
        return True
    except Exception:  # noqa: BLE001
        return False


def start_backup_loop() -> threading.Thread:
    """后台线程：启动后先备份一次，此后每隔 backup_interval_seconds 备份一次。"""

    def _loop():
        while True:
            try:
                from . import db  # 延迟导入，避免循环依赖
                db.backup_database()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(settings.backup_interval_seconds)

    t = threading.Thread(target=_loop, daemon=True, name="db-backup")
    t.start()
    return t
