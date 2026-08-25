"""天气/日照查询：真实数据（和风天气新版 API）优先，mock 降级。

新版和风 API：专属 API Host + X-QW-Api-Key 认证；
- 逐小时：/weather/v1/hourly/{lat}/{lon}
- 每日（含日出日落）：/weather/v1/daily/{lat}/{lon}
返回结构保持 meta/hourly/sunrise/sunset 不变，上层无需改动。
"""
from __future__ import annotations

import re
from datetime import datetime, time

import httpx

from ..core.config import settings
from . import geo

_WIND_ZH = {
    "n": "北风", "nne": "北东北风", "ne": "东北风", "ene": "东东北风",
    "e": "东风", "ese": "东东南风", "se": "东南风", "sse": "南东南风",
    "s": "南风", "ssw": "南西南风", "sw": "西南风", "wsw": "西西南风",
    "w": "西风", "wnw": "西西北风", "nw": "西北风", "nnw": "北西北风",
}


def get_hourly(location: str | None, target_date: datetime | None = None) -> dict:
    """优先真实天气；无 Key/Host、地点无效或调用失败时降级 mock。"""
    if target_date is None:
        target_date = datetime.now()
    real = _get_real(location)
    if real is not None:
        return real
    return _mock(location, target_date)


def _get_real(location: str | None) -> dict | None:
    if not geo.is_configured() or not location:
        return None
    try:
        place = geo.lookup_location(location)
        if not place or not place.get("lat") or not place.get("lon"):
            return None
        host = settings.qweather_api_host
        headers = {"X-QW-Api-Key": settings.qweather_key}
        lat, lon = place["lat"], place["lon"]

        # 逐小时
        r1 = httpx.get(
            f"https://{host}/weather/v1/hourly/{lat}/{lon}",
            params={"hours": 24, "lang": "zh", "localTime": "true"},
            headers=headers,
            timeout=10.0,
        )
        d1 = r1.json()
        hours_raw = d1.get("hours")
        if not hours_raw:
            return None

        # 日出日落（每日预报含 astro）
        sunrise, sunset = "06:00", "18:00"
        try:
            r2 = httpx.get(
                f"https://{host}/weather/v1/daily/{lat}/{lon}",
                params={"days": 1, "lang": "zh", "localTime": "true"},
                headers=headers,
                timeout=10.0,
            )
            d2 = r2.json()
            days = d2.get("days")
            if days:
                astro = days[0].get("astro") or {}
                sunrise = _hhmm(astro.get("sunrise")) or sunrise
                sunset = _hhmm(astro.get("sunset")) or sunset
        except Exception:  # noqa: BLE001
            pass

        hourly = []
        for i, h in enumerate(hours_raw):
            pressure = _num(h.get("pressure", {}).get("value"))
            prev = _num(hours_raw[i - 1].get("pressure", {}).get("value")) if i > 0 else pressure
            hourly.append(
                {
                    "time": h.get("forecastTime", ""),
                    "temp": round(_num(h.get("temperature", {}).get("value"))),
                    "precip_prob": round(_num(h.get("precipitation", {}).get("probability")) * 100),
                    "wind_scale": int(_num(h.get("wind", {}).get("scale"))),
                    "wind_dir": _wind_zh(h.get("wind", {}).get("direction", {}).get("compass")),
                    "pressure": pressure,
                    "pressure_trend": _trend(prev, pressure),
                    "condition": h.get("condition", {}).get("text", ""),
                }
            )

        return {
            "meta": {
                "location": place.get("name", location),
                "source": "qweather",
                "mock": False,
                "updated_at": datetime.now().isoformat(timespec="minutes"),
            },
            "sunrise": sunrise,
            "sunset": sunset,
            "hourly": hourly,
        }
    except Exception:  # noqa: BLE001
        return None


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _wind_zh(compass) -> str:
    return _WIND_ZH.get(str(compass).lower(), str(compass) or "—")


def _hhmm(iso: str | None) -> str | None:
    if not iso:
        return None
    m = re.search(r"T(\d{2}:\d{2})", str(iso))
    return m.group(1) if m else None


def _trend(prev: float, cur: float) -> str:
    if cur > prev + 0.1:
        return "缓升"
    if cur < prev - 0.1:
        return "下降"
    return "平稳"


def _mock(location: str | None, target_date: datetime) -> dict:
    """确定性 mock：供无 Key/Host 或真实数据失败时降级。"""
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
