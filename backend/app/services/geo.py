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


def reverse_lookup(lat: float, lon: float) -> dict | None:
    """经纬度 → 地点（逆地理编码）；失败返回 None。"""
    if not is_configured():
        return None
    try:
        url = f"https://{settings.qweather_api_host}/geo/v2/city/lookup"
        # 和风 GeoAPI 支持 "经度,纬度" 坐标反查
        resp = httpx.get(
            url,
            params={"location": f"{lon},{lat}", "lang": "zh"},
            headers=_headers(),
            timeout=10.0,
        )
        data = resp.json()
        if data.get("location"):
            loc = data["location"][0]
            return {
                "id": loc.get("id"),
                "name": loc.get("adm2") or loc.get("name"),  # 市级优先，更符合用户认知
                "district": loc.get("name"),  # 区级保留
                "adm2": loc.get("adm2"),
                "adm1": loc.get("adm1"),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
            }
    except Exception:  # noqa: BLE001
        pass
    return None
