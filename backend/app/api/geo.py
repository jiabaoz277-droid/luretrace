"""地理位置接口：逆地理编码（经纬度 → 地点）。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..services import geo

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/reverse")
def reverse(lat: float = Query(...), lon: float = Query(...)):
    place = geo.reverse_lookup(lat, lon)
    if not place:
        return {"name": None}
    return place
