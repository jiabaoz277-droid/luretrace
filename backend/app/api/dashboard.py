"""实时天气 + 附近钓点聚合接口（首页看板）。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from ..services import geo, waters, weather
from ..services.decision import hourly_fish_scores

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    place: str | None = Query(None),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
):
    """按地点或坐标返回：当前天气 + 逐小时 + 日出日落 + 附近钓点。"""
    name = place

    # 有坐标：反查名称 + 用坐标找钓点
    if lat is not None and lon is not None:
        if not name:
            rev = geo.reverse_lookup(lat, lon)
            name = (rev or {}).get("name") or (rev or {}).get("district")
    elif name:
        loc = geo.lookup_location(name)
        if loc and loc.get("lat") and loc.get("lon"):
            lat, lon = float(loc["lat"]), float(loc["lon"])

    if not name and lat is None:
        return {"location": None, "current": None, "spots": [], "mock": False}

    # 天气（真实优先，失败降级 mock）
    w = weather.get_hourly(name)
    hourly = w.get("hourly", [])
    now_hour = datetime.now().hour
    current = None
    for h in hourly:
        try:
            if int(h["time"][11:13]) == now_hour:
                current = h
                break
        except (ValueError, IndexError):
            continue
    if current is None and hourly:
        current = hourly[0]

    # 附近钓点
    spots: list[dict] = []
    if lat is not None and lon is not None:
        spots = waters.find_spots(lat=lat, lon=lon)
    elif name:
        spots = waters.find_spots(place=name)

    return {
        "location": name,
        "current": current,
        "sunrise": w.get("sunrise"),
        "sunset": w.get("sunset"),
        "hourly": hourly,
        "fish_scores": hourly_fish_scores(hourly),
        "spots": spots,
        "mock": bool((w.get("meta") or {}).get("mock", False)),
    }
