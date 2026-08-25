"""配置读取：从环境变量加载，不含真实密钥。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（backend/app/core/config.py 的上级上级上级）
BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        self.model_api_key: str = os.getenv("MODEL_API_KEY", "")
        self.model_base_url: str = os.getenv("MODEL_BASE_URL", "")
        self.model_name: str = os.getenv("MODEL_NAME", "")
        # 真实天气/地理数据源（和风天气 QWeather，免费额度）
        self.qweather_key: str = os.getenv("QWEATHER_KEY", "")
        self.qweather_api_host: str = os.getenv("QWEATHER_API_HOST", "")  # 专属 API Host，如 xxx.qweatherapi.com
        self.database_url: str = os.getenv(
            "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'fishing.db'}"
        )
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS", "http://localhost:3000,http://localhost:3002"
            ).split(",")
            if o.strip()
        ]
        self.api_prefix: str = "/api/v1"


settings = Settings()
