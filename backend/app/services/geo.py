"""地理位置解析（和风天气 GeoAPI v2，专属 API Host）：地点文本 → 经纬度。"""
from __future__ import annotations

import httpx

from ..core.config import settings


def is_configured() -> bool:
    return bool(settings.qweather_key and settings.qweather_api_host)


def _headers() -> dict:
    return {"X-QW-Api-Key": settings.qweather_key}


def lookup_location(text: str) -> dict | None:
    """地点文本 → {id, name, lat, lon}；失败或无 Key/Host 返回 None（由调用方降级）。"""
    if not is_configured() or not text:
        return None
    try:
        url = f"https://{settings.qweather_api_host}/geo/v2/city/lookup"
        resp = httpx.get(
            url,
            params={"location": text, "lang": "zh"},
            headers=_headers(),
            timeout=10.0,
        )
        data = resp.json()
        if data.get("location"):
            loc = data["location"][0]
            return {
                "id": loc.get("id"),
                "name": loc.get("name", text),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
            }
    except Exception:  # noqa: BLE001
        pass
    return None
