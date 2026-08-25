"""地理位置解析（和风天气 GeoAPI）：地点文本 → 经纬度 + location id。"""
from __future__ import annotations

import httpx

from ..core.config import settings

_GEO_URL = "https://geoapi.qweather.com/v2/city/lookup"


def is_configured() -> bool:
    return bool(settings.qweather_key)


def lookup_location(text: str) -> dict | None:
    """地点文本 → {id, name, lat, lon}；失败或无 Key 返回 None（由调用方降级）。"""
    if not is_configured() or not text:
        return None
    try:
        resp = httpx.get(
            _GEO_URL,
            params={"location": text, "key": settings.qweather_key},
            timeout=10.0,
        )
        data = resp.json()
        if data.get("code") == "200" and data.get("location"):
            loc = data["location"][0]
            return {
                "id": loc["id"],
                "name": loc.get("name", text),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
            }
    except Exception:  # noqa: BLE001
        pass
    return None
