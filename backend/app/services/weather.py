"""天气/日照查询：真实数据（和风天气新版 API）优先，mock 降级。

新版和风 API：专属 API Host + X-QW-Api-Key 认证；
- 逐小时：/weather/v1/hourly/{lat}/{lon}
- 每日（含日出日落）：/weather/v1/daily/{lat}/{lon}
返回结构保持 meta/hourly/sunrise/sunset 不变，上层无需改动。
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, time, timedelta

import httpx

from ..core.config import settings
from . import geo

logger = logging.getLogger(__name__)

_WIND_ZH = {
    "n": "北风", "nne": "北东北风", "ne": "东北风", "ene": "东东北风",
    "e": "东风", "ese": "东东南风", "se": "东南风", "sse": "南东南风",
    "s": "南风", "ssw": "南西南风", "sw": "西南风", "wsw": "西西南风",
    "w": "西风", "wnw": "西西北风", "nw": "西北风", "nnw": "北西北风",
}


def get_hourly(
    location: str | None,
    target_date: datetime | None = None,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """优先真实天气；降级时在 meta.warning 中明确告知上层。"""
    if target_date is None:
        target_date = datetime.now()
    if not geo.is_configured():
        return _mock(location, target_date, "实时天气未配置，当前为演示数据")
    if not location and (lat is None or lon is None):
        return _mock(location, target_date, "未获取到有效位置，当前为演示数据")
    try:
        real = _get_real(location, lat=lat, lon=lon)
    except Exception:  # noqa: BLE001
        logger.exception("QWeather hourly request failed")
        return _mock(location, target_date, "实时天气暂时不可用，当前为演示数据")
    if real is not None:
        return real
    return _mock(location, target_date, "未查到该位置的实时天气，当前为演示数据")


def _get_real(
    location: str | None,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> dict | None:
    if not geo.is_configured():
        return None
    if lat is None or lon is None:
        if not location:
            return None
        place = geo.lookup_location(location)
        if not place or not place.get("lat") or not place.get("lon"):
            return None
        lat, lon = place["lat"], place["lon"]
    else:
        place = {"name": location or "当前位置", "lat": lat, "lon": lon}
    host = settings.qweather_api_host
    headers = {"X-QW-Api-Key": settings.qweather_key}

    # 逐小时
    r1 = httpx.get(
        f"https://{host}/weather/v1/hourly/{lat}/{lon}",
        params={"hours": 24, "lang": "zh", "localTime": "true"},
        headers=headers,
        timeout=10.0,
    )
    r1.raise_for_status()
    d1 = r1.json()
    hours_raw = d1.get("hours")
    if not hours_raw:
        return None

    # 日出日落（失败不影响已获取的小时天气，但保留日志）
    sunrise, sunset = "06:00", "18:00"
    try:
        r2 = httpx.get(
            f"https://{host}/weather/v1/daily/{lat}/{lon}",
            params={"days": 1, "lang": "zh", "localTime": "true"},
            headers=headers,
            timeout=10.0,
        )
        r2.raise_for_status()
        d2 = r2.json()
        days = d2.get("days")
        if days:
            astro = days[0].get("astro") or {}
            sunrise = _hhmm(astro.get("sunrise")) or sunrise
            sunset = _hhmm(astro.get("sunset")) or sunset
    except Exception:  # noqa: BLE001
        logger.warning("QWeather daily/astro request failed", exc_info=True)

    hourly = []
    for i, h in enumerate(hours_raw):
        pressure = _num(h.get("pressure", {}).get("value"))
        prev = _num(hours_raw[i - 1].get("pressure", {}).get("value")) if i > 0 else pressure
        hourly.append(
            {
                "time": h.get("forecastTime", ""),
                "temp": round(_num(h.get("temperature", {}).get("value"))),
                "precip_prob": round(_probability(h.get("precipitation", {}).get("probability"))),
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
            "degraded": False,
            "warning": None,
            "updated_at": datetime.now().isoformat(timespec="minutes"),
        },
        "sunrise": sunrise,
        "sunset": sunset,
        "hourly": hourly,
    }


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _probability(v) -> float:
    """兼容上游返回 0–1 小数或 0–100 百分数。"""
    value = _num(v)
    return max(0.0, min(100.0, value * 100 if value <= 1 else value))


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


def _mock(location: str | None, target_date: datetime, warning: str | None = None) -> dict:
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
            "degraded": True,
            "warning": warning or "当前为演示数据",
            "updated_at": datetime.now().isoformat(timespec="minutes"),
        },
        "sunrise": "05:20",
        "sunset": "18:50",
        "hourly": hourly,
    }


# ---------- 逐日预报（多日出钓规划用） ----------


def get_daily_forecast(location: str | None, days: int = 7) -> list[dict]:
    """未来 N 天逐日预报；真实数据失败降级 mock。返回逐日摘要列表。"""
    if not geo.is_configured():
        return _daily_mock(location, days, "实时天气未配置，当前为演示数据")
    real = _get_daily_real(location, days)
    if real:
        return real
    return _daily_mock(location, days, "多日预报暂时不可用，当前为演示数据")


def _get_daily_real(location: str | None, days: int) -> list[dict] | None:
    if not geo.is_configured() or not location:
        return None
    try:
        place = geo.lookup_location(location)
        if not place or not place.get("lat") or not place.get("lon"):
            return None
        host = settings.qweather_api_host
        headers = {"X-QW-Api-Key": settings.qweather_key}
        lat, lon = place["lat"], place["lon"]
        resp = httpx.get(
            f"https://{host}/weather/v1/daily/{lat}/{lon}",
            params={"days": days, "lang": "zh", "localTime": "true"},
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        days_raw = data.get("days") or data.get("daily") or []
        if not days_raw:
            return None
        result = []
        for dd in days_raw[:days]:
            dt = dd.get("daytime") or {}
            nt = dd.get("nighttime") or {}
            astro = dd.get("astro") or {}
            p_day = _num(dt.get("precipitation", {}).get("probability"))
            p_night = _num(nt.get("precipitation", {}).get("probability"))
            precip_prob = max(_probability(p_day), _probability(p_night))
            wind = dt.get("wind") or {}
            fx = dd.get("forecastStartTime") or ""
            result.append(
                {
                    "date": fx[:10] if fx else "",
                    "temp_max": _num(dd.get("temperatureMax", {}).get("value")),
                    "temp_min": _num(dd.get("temperatureMin", {}).get("value")),
                    "condition": (dt.get("condition") or {}).get("text", ""),
                    "precip_prob": round(precip_prob),
                    "wind_scale": int(_num(wind.get("scale"))),
                    "wind_dir": _wind_zh(wind.get("direction", {}).get("compass")),
                    "sunrise": _hhmm(astro.get("sunrise")) or "06:00",
                    "sunset": _hhmm(astro.get("sunset")) or "18:00",
                    "source": "qweather",
                    "mock": False,
                    "warning": None,
                }
            )
        return result
    except Exception:  # noqa: BLE001
        logger.exception("QWeather daily forecast request failed")
        return None


def _daily_mock(
    location: str | None,
    days: int,
    warning: str | None = None,
) -> list[dict]:
    today = datetime.now().date()
    conditions = ["多云", "晴", "小雨", "阴", "晴", "雷阵雨", "多云"]
    precip = [10, 5, 45, 20, 5, 80, 10]
    result = []
    for i in range(days):
        d = today + timedelta(days=i)
        seed = (d.day + i) % 7
        result.append(
            {
                "date": d.isoformat(),
                "temp_max": 30 + seed % 5,
                "temp_min": 22 + seed % 4,
                "condition": conditions[seed],
                "precip_prob": precip[seed],
                "wind_scale": 2 + seed % 3,
                "wind_dir": "东风" if seed % 2 == 0 else "东南风",
                "sunrise": "05:20",
                "sunset": "18:50",
                "source": "mock",
                "mock": True,
                "warning": warning or "当前为演示数据",
            }
        )
    return result
