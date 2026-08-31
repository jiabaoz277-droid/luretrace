"""地理位置接口：逆地理编码（经纬度 → 地点）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..core import rate_limit
from ..core.auth import current_user_id
from ..core.config import settings
from ..services import geo

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/reverse")
def reverse(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    wait = rate_limit.check_action(
        f"upstream:{current_user_id(request)}", limit=settings.upstream_rate_limit,
        window_seconds=settings.api_rate_window_seconds,
    )
    if wait:
        raise HTTPException(status_code=429, detail={"code": "rate_limited", "message": "请求太频繁，请稍后再试"}, headers={"Retry-After": str(wait)})
    place = geo.reverse_lookup(lat, lon)
    if not place:
        return {"name": None}
    return place
