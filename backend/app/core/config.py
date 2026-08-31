"""配置读取：从环境变量加载，不含真实密钥。

生产环境（ENV=prod）通过 veFaaS 环境变量注入；本地开发从项目根 .env 读取。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（backend/app/core/config.py 的上级上级上级）
BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


def _as_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.env: str = os.getenv("ENV", "dev")
        self.is_prod: bool = self.env == "prod"

        # 模型（OpenAI 兼容接口，DeepSeek 默认；火山方舟替换 BASE_URL/NAME）
        self.model_api_key: str = os.getenv("MODEL_API_KEY", "")
        self.model_base_url: str = os.getenv("MODEL_BASE_URL", "")
        self.model_name: str = os.getenv("MODEL_NAME", "")

        # 真实天气/地理数据源（和风天气 QWeather）
        self.qweather_key: str = os.getenv("QWEATHER_KEY", "")
        self.qweather_api_host: str = os.getenv("QWEATHER_API_HOST", "")

        # 数据库：生产环境默认写到 /tmp（veFaaS 实例除 /tmp 外只读）；
        # 本地沿用 data/ 目录。显式配置 DATABASE_URL 时以配置为准。
        default_db = (
            "sqlite:////tmp/data/app.db"
            if self.is_prod
            else f"sqlite:///{BASE_DIR / 'data' / 'fishing.db'}"
        )
        self.database_url: str = os.getenv("DATABASE_URL", default_db)

        self.cors_origins: list[str] = _as_list(
            os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3002")
        )

        # 登录（邀请码换 token）
        self.invite_codes: list[str] = _as_list(os.getenv("INVITE_CODES", ""))
        # 提示词管理后台令牌（X-Admin-Token）；未配置时后台不可用
        self.admin_token: str = os.getenv("ADMIN_TOKEN", "")
        # 生产环境必须显式配置 TOKEN_SECRET；未配置时签发 token 会失败（见 core/auth.py）
        self.token_secret: str = os.getenv(
            "TOKEN_SECRET", "dev-insecure-secret-change-me" if not self.is_prod else ""
        )
        self.token_ttl_seconds: int = int(os.getenv("TOKEN_TTL_SECONDS", "604800"))  # 7 天
        self.login_rate_limit: int = int(os.getenv("LOGIN_RATE_LIMIT", "5"))
        self.login_rate_window_seconds: int = int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "300"))
        self.login_block_seconds: int = int(os.getenv("LOGIN_BLOCK_SECONDS", "900"))
        self.chat_rate_limit: int = int(os.getenv("CHAT_RATE_LIMIT", "20"))
        self.upstream_rate_limit: int = int(os.getenv("UPSTREAM_RATE_LIMIT", "60"))
        self.api_rate_window_seconds: int = int(os.getenv("API_RATE_WINDOW_SECONDS", "60"))

        self.api_prefix: str = "/api/v1"

        # 上传文件目录：生产环境只能写 /tmp（接入对象存储前先用 /tmp 落盘）
        self.upload_dir: str = os.getenv(
            "UPLOAD_DIR",
            "/tmp/data/uploads" if self.is_prod else str(BASE_DIR / "data" / "uploads"),
        )

        # 地图水域数据源（OpenStreetMap Overpass）
        self.overpass_url: str = os.getenv(
            "OVERPASS_URL", "https://overpass-api.de/api/interpreter"
        )
        # 高德地图（Amap）
        self.amap_key: str = os.getenv("AMAP_KEY", "")

        # 错误监控（可选）
        self.sentry_dsn: str = os.getenv("SENTRY_DSN", "")

        # 对象存储备份（可选；未配置 S3 时退化为本地 /tmp 副本）
        self.storage_provider: str = os.getenv("STORAGE_PROVIDER", "")
        self.s3_endpoint: str = os.getenv("S3_ENDPOINT", "")
        self.s3_access_key: str = os.getenv("S3_ACCESS_KEY", "")
        self.s3_secret_key: str = os.getenv("S3_SECRET_KEY", "")
        self.s3_bucket: str = os.getenv("S3_BUCKET", "")
        self.s3_region: str = os.getenv("S3_REGION", "cn-beijing")
        self.backup_interval_seconds: int = int(os.getenv("BACKUP_INTERVAL_SECONDS", "300"))

        # 生产默认关闭 API 文档和模型诊断信息，可显式开启。
        self.expose_api_docs: bool = _as_bool(
            os.getenv("EXPOSE_API_DOCS", "false" if self.is_prod else "true")
        )
        self.expose_model_status: bool = _as_bool(
            os.getenv("EXPOSE_MODEL_STATUS", "false" if self.is_prod else "true")
        )


settings = Settings()
