"""实时天气 + 附近钓点聚合接口（首页看板）。"""
from __future__ import annotations

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Query, Request

from ..core import rate_limit
from ..core.auth import current_user_id
from ..core.config import settings
from ..services import geo, waters, weather
from ..services.decision import hourly_fish_scores

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    request: Request,
    place: str | None = Query(None, max_length=128),
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    target_species: str | None = Query(None, max_length=64),
    max_travel_minutes: int | None = Query(None, ge=1, le=1440),
):
    """按地点或坐标返回：当前天气 + 逐小时 + 日出日落 + 附近钓点。"""
    wait = rate_limit.check_action(
        f"upstream:{current_user_id(request)}", limit=settings.upstream_rate_limit,
        window_seconds=settings.api_rate_window_seconds,
    )
    if wait:
        raise HTTPException(status_code=429, detail={"code": "rate_limited", "message": "请求太频繁，请稍后再试"}, headers={"Retry-After": str(wait)})
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

    # 天气与钓点是独立上游，并行查询减少首页等待。
    def _load_spots() -> list[dict]:
        if lat is not None and lon is not None:
            return waters.find_spots(
                lat=lat,
                lon=lon,
                target_species=target_species,
                max_travel_minutes=max_travel_minutes,
            )
        if name:
            return waters.find_spots(
                place=name,
                target_species=target_species,
                max_travel_minutes=max_travel_minutes,
            )
        return []

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="dashboard") as executor:
        weather_future = executor.submit(weather.get_hourly, name, None, lat=lat, lon=lon)
        spots_future = executor.submit(_load_spots)
        w = weather_future.result()
        spots = spots_future.result()

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

    meta = w.get("meta") or {}
    warnings = [meta["warning"]] if meta.get("warning") else []
    return {
        "location": name,
        "current": current,
        "sunrise": w.get("sunrise"),
        "sunset": w.get("sunset"),
        "hourly": hourly,
        "fish_scores": hourly_fish_scores(hourly),
        "spots": spots,
        "mock": bool(meta.get("mock", False)),
        "data_status": "degraded" if meta.get("mock") else "live",
        "warnings": warnings,
    }
