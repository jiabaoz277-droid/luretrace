"""天气/日照查询：真实数据（和风天气）优先，mock 降级。

返回结构保持不变（meta/hourly/sunrise/sunset），上层决策引擎无需改动。
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta

import httpx

from ..core.config import settings
from . import geo

_WEATHER_URL = "https://devapi.qweather.com/v7/weather/24h"
_SUN_URL = "https://devapi.qweather.com/v7/astronomy/sun"


def get_hourly(location: str | None, target_date: datetime | None = None) -> dict:
    """优先真实天气；无 Key、地点无效或调用失败时降级 mock。"""
    if target_date is None:
        target_date = datetime.now()
    real = _get_real(location, target_date)
    if real is not None:
        return real
    return _mock(location, target_date)


def _get_real(location: str | None, target_date: datetime) -> dict | None:
    if not geo.is_configured() or not location:
        return None
    try:
        place = geo.lookup_location(location)
        if not place:
            return None

        resp = httpx.get(
            _WEATHER_URL,
            params={"location": place["id"], "key": settings.qweather_key},
            timeout=10.0,
        )
        data = resp.json()
        if data.get("code") != "200" or not data.get("hourly"):
            return None
        hourly_raw = data["hourly"]

        hourly = []
        for i, h in enumerate(hourly_raw):
            prev = hourly_raw[i - 1]["pressure"] if i > 0 else h["pressure"]
            hourly.append(
                {
                    "time": h["fxTime"],
                    "temp": int(h.get("temp", 0)),
                    "precip_prob": int(h.get("pop", 0)),
                    "wind_scale": _wind_scale(h.get("windScale", "")),
                    "wind_dir": h.get("windDir", ""),
                    "pressure": int(h.get("pressure", 0)),
                    "pressure_trend": _trend(prev, h.get("pressure", 0)),
                    "condition": h.get("text", ""),
                }
            )

        sunrise, sunset = _get_sun(place["id"], target_date)
        return {
            "meta": {
                "location": place.get("name", location),
                "source": "qweather",
                "mock": False,
                "updated_at": data.get("updateTime") or datetime.now().isoformat(timespec="minutes"),
            },
            "sunrise": sunrise,
            "sunset": sunset,
            "hourly": hourly,
        }
    except Exception:  # noqa: BLE001
        return None


def _get_sun(location_id: str, target_date: datetime) -> tuple[str, str]:
    try:
        resp = httpx.get(
            _SUN_URL,
            params={
                "location": location_id,
                "date": target_date.strftime("%Y%m%d"),
                "key": settings.qweather_key,
            },
            timeout=10.0,
        )
        data = resp.json()
        return data.get("sunrise", "06:00"), data.get("sunset", "18:00")
    except Exception:  # noqa: BLE001
        return "06:00", "18:00"


def _wind_scale(raw: str | int) -> int:
    if isinstance(raw, int):
        return raw
    m = re.search(r"\d+", str(raw))
    return int(m.group()) if m else 0


def _trend(prev: str | int, cur: str | int) -> str:
    try:
        p, c = int(prev), int(cur)
        if c > p:
            return "缓升"
        if c < p:
            return "下降"
    except (TypeError, ValueError):
        pass
    return "平稳"


def _mock(location: str | None, target_date: datetime) -> dict:
    """确定性 mock：供无 Key 或真实数据失败时降级。"""
    day = target_date.date()
    seed = day.day % 7
    hourly = []
    for h in range(24):
        if h < 9:
            precip, wind, cond = 10 + seed, 2, "多云"
        elif h < 16:
            precip, wind, cond = 55 + seed * 3, 3, "多云转阵雨"
        else:
            precip, wind, cond = 25 + seed, 2, "多云"
        pressure = 1008 + (h // 6)
        trend = "缓升" if h < 12 else "平稳"
        hourly.append(
            {
                "time": datetime.combine(day, time(h, 0)).isoformat(),
                "temp": 24 + (1 if 10 <= h <= 16 else 0),
                "precip_prob": min(precip, 90),
                "wind_scale": wind,
                "wind_dir": "东风",
                "pressure": pressure,
                "pressure_trend": trend,
                "condition": cond,
            }
        )
    return {
        "meta": {
            "location": location or "未知",
            "source": "mock",
            "mock": True,
            "updated_at": datetime.now().isoformat(timespec="minutes"),
        },
        "sunrise": "05:20",
        "sunset": "18:50",
        "hourly": hourly,
    }
