"""水域与标点分析：OpenStreetMap Overpass → 回水湾 / 入水口等候选钓点。

- 数据源：Overpass API（免费、无需 Key），查询附近河道与溪流。
- 几何启发：河道明显拐弯 → 回水湾；两条水道端点相近 → 入水口/汇口。
- 失败或无数据一律返回 []，由上层降级为通用标点类型建议，绝不编造点位。
"""
from __future__ import annotations

import math

import httpx

from ..core.config import settings
from . import geo
from .knowledge import get_species

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_TIMEOUT = 15.0

# 回水湾的原因文案
_BEND_REASON = "河道在这里拐弯，水流放缓，掠食鱼爱在湾口伏击小鱼"
_CONFLUENCE_REASON = "两条水道在这里交汇，溶氧高、小鱼多，是入水口型标点"


# ---------- 几何工具（纯函数，便于单测） ----------


def _haversine(a: tuple[float, float], b: tuple[float, float], r: float = 6371000.0) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ---------- WGS-84 → GCJ-02（火星坐标）----------
# OSM 是 WGS-84，高德地图用 GCJ-02，直接画会有数百米偏移，需转换。

_PI = math.pi
_A = 6378245.0
_EE = 0.00669342162296594323


def _out_of_china(lat: float, lon: float) -> bool:
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * _PI) + 40.0 * math.sin(y / 3.0 * _PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * _PI) + 320.0 * math.sin(y * _PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * _PI) + 40.0 * math.sin(x / 3.0 * _PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * _PI) + 300.0 * math.sin(x / 30.0 * _PI)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lat: float, lon: float) -> tuple[float, float]:
    """WGS-84 → GCJ-02，境外坐标原样返回。"""
    if _out_of_china(lat, lon):
        return lat, lon
    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * _PI
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * _PI)
    dlon = (dlon * 180.0) / (_A / sqrtmagic * math.cos(radlat) * _PI)
    return lat + dlat, lon + dlon


def _resample(points: list[tuple[float, float]], spacing: float) -> list[tuple[float, float]]:
    """沿折线按固定间距重新采样（等距点列，避免节点密度偏差）。"""
    if len(points) < 2:
        return points
    cum = [0.0]
    for i in range(1, len(points)):
        d = math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
        cum.append(cum[-1] + d)
    total = cum[-1]
    if total <= 0:
        return points
    out = [points[0]]
    target = spacing
    i = 1
    while target < total and i < len(points):
        if cum[i] >= target:
            seg = cum[i] - cum[i - 1]
            t = (target - cum[i - 1]) / seg if seg > 0 else 0.0
            x = points[i - 1][0] + (points[i][0] - points[i - 1][0]) * t
            y = points[i - 1][1] + (points[i][1] - points[i - 1][1]) * t
            out.append((x, y))
            target += spacing
        else:
            i += 1
    out.append(points[-1])
    return out


def _bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _turn(b1: float, b2: float) -> float:
    """相邻两段航向的转角，归一化到 (-180, 180]。"""
    return (b2 - b1 + 180.0) % 360.0 - 180.0


def find_bends(
    geometry: list[tuple[float, float]],
    spacing: float = 60.0,
    min_turn: float = 45.0,
) -> list[tuple[float, float]]:
    """在河道折线中找明显拐弯点，返回 (lat, lon) 列表（回水湾候选）。"""
    if len(geometry) < 4:
        return []
    lat0, lon0 = geometry[0]
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    xy = [((lon - lon0) * kx, (lat - lat0) * ky) for lat, lon in geometry]
    pts = _resample(xy, spacing)
    if len(pts) < 4:
        return []
    bearings = [_bearing(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    turns = [_turn(bearings[i], bearings[i + 1]) for i in range(len(bearings) - 1)]

    bends: list[tuple[float, float]] = []
    i, n = 0, len(turns)
    while i < n:
        if abs(turns[i]) < 15.0:
            i += 1
            continue
        acc = turns[i]
        sign = 1.0 if turns[i] > 0 else -1.0
        peak = acc
        peak_j = i
        j = i + 1
        while j < n and abs(turns[j]) >= 5.0 and turns[j] * sign > 0:
            acc += turns[j]
            if abs(acc) > abs(peak):
                peak = acc
                peak_j = j
            j += 1
        if abs(peak) >= min_turn:
            bx, by = pts[peak_j + 1]
            bends.append((lat0 + by / ky, lon0 + bx / kx))
        i = max(j, i + 1)
    return bends


def _nearest(
    geometry: list[tuple[float, float]], ref: tuple[float, float]
) -> tuple[float, float]:
    """返回距参考点最近的几何点。"""
    best = geometry[0]
    best_d = _haversine(ref, best)
    for p in geometry[1:]:
        d = _haversine(ref, p)
        if d < best_d:
            best_d = d
            best = p
    return best


def find_confluences(
    ways: list[dict],
    max_gap_m: float = 150.0,
    limit: int = 3,
) -> list[tuple[float, float]]:
    """两条水道端点相近 → 入水口/汇口候选，返回 (lat, lon) 列表。"""
    endpoints: list[tuple[float, float]] = []
    for w in ways:
        g = w.get("geometry") or []
        glatlon = [(p["lat"], p["lon"]) for p in g] if g else []
        if len(glatlon) >= 2:
            endpoints.append(glatlon[0])
            endpoints.append(glatlon[-1])
    result: list[tuple[float, float]] = []
    for i in range(len(endpoints)):
        for j in range(i + 1, len(endpoints)):
            if _haversine(endpoints[i], endpoints[j]) <= max_gap_m:
                result.append(
                    ((endpoints[i][0] + endpoints[j][0]) / 2, (endpoints[i][1] + endpoints[j][1]) / 2)
                )
    return result[:limit]


# ---------- 数据查询 ----------


def _query_overpass(
    lat: float, lon: float, radius_m: float
) -> tuple[list[dict], list[list[tuple[float, float]]]]:
    """一次查询同时获取水域 ways 与保护区多边形，返回 (ways, protected_polys)。"""
    url = settings.overpass_url or DEFAULT_OVERPASS_URL
    ql = (
        "[out:json][timeout:20];"
        "("
        f'way["waterway"="river"](around:{radius_m},{lat},{lon});'
        f'way["waterway"="stream"](around:{radius_m},{lat},{lon});'
        f'way["natural"="water"](around:{radius_m},{lat},{lon});'
        f'way["boundary"="protected_area"](around:{radius_m},{lat},{lon});'
        f'way["leisure"="nature_reserve"](around:{radius_m},{lat},{lon});'
        ");"
        "out geom;"
    )
    # Overpass 要求合法 User-Agent，否则返回 406
    resp = httpx.post(
        url,
        data={"data": ql},
        timeout=_TIMEOUT,
        headers={"User-Agent": "lure-helper/0.1 (fishing-assistant)"},
    )
    resp.raise_for_status()
    data = resp.json()
    ways: list[dict] = []
    protected: list[list[tuple[float, float]]] = []
    for e in data.get("elements", []):
        if e.get("type") != "way":
            continue
        tags = e.get("tags") or {}
        if tags.get("boundary") == "protected_area" or tags.get("leisure") == "nature_reserve":
            g = e.get("geometry") or []
            glatlon = [(p["lat"], p["lon"]) for p in g]
            if len(glatlon) >= 4:
                protected.append(glatlon)
        else:
            ways.append(e)
    return ways, protected


def _amap_pois(
    lat: float,
    lon: float,
    radius_m: float,
    keywords: str,
    limit: int = 3,
    type_filter: str | None = None,
) -> list[dict]:
    """高德 POI 周边搜索。返回 [{name, type, lat, lon}]；失败或无 Key 返回 []。"""
    if not settings.amap_key:
        return []
    try:
        resp = httpx.get(
            "https://restapi.amap.com/v3/place/around",
            params={
                "key": settings.amap_key,
                "location": f"{lon},{lat}",  # 高德坐标为 lng,lat
                "radius": int(radius_m),
                "keywords": keywords,
                "offset": limit,
                "page": 1,
                "extensions": "base",
            },
            timeout=10.0,
        )
        data = resp.json()
        if data.get("status") != "1":
            return []
        pois: list[dict] = []
        for p in data.get("pois", []):
            ptype = p.get("type") or ""
            if type_filter and type_filter not in ptype:
                continue
            loc = p.get("location") or ""
            if "," not in loc:
                continue
            plng, plat = loc.split(",", 1)
            try:
                pois.append(
                    {
                        "name": p.get("name") or "附近水域",
                        "type": ptype,
                        "lat": float(plat),
                        "lon": float(plng),
                    }
                )
            except ValueError:
                continue
        return pois
    except Exception:  # noqa: BLE001
        return []


# ---------- 鱼种标点匹配 ----------

# 鱼种 spots 关键词 → 候选 spot_type（用于按鱼种习性优先推荐）
_SPOT_TYPE_MATCH: dict[str, list[str]] = {
    "回水湾": ["湾口", "回水湾", "洄水", "背风岸"],
    "入水口": ["入水口", "汇口", "支流汇口", "急缓流交界", "急流边", "流水缓区"],
    "近岸": [
        "近岸", "岸边", "浅滩", "水草", "草洞", "芦苇", "浮萍", "荷叶",
        "枯木", "码头桩", "岩石", "乱石", "碎石", "桥墩", "障碍",
        "深浅交界", "明暗交界", "下风处",
    ],
    "钓场": [],
    "水域": [],
}


def _species_prefers(species_spots: list[str], spot_type: str) -> bool:
    """判断候选标点类型是否命中目标鱼偏好。"""
    keys = _SPOT_TYPE_MATCH.get(spot_type, [])
    if not keys:
        return False
    return any(any(k in s for k in keys) for s in species_spots)


# ---------- 禁钓区域（保护区）----------


def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    """射线法判断点是否在多边形内（坐标均为 lat,lon）。"""
    lat, lon = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]
        if ((lon_i > lon) != (lon_j > lon)) and (
            lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i
        ):
            inside = not inside
        j = i
    return inside


# ---------- 对外入口 ----------


def find_spots(
    place: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float = 5000.0,
    limit: int = 3,
    target_species: str | None = None,
    max_travel_minutes: int | None = None,
    max_distance_km: float | None = None,
) -> list[dict]:
    """查询附近水域并分析候选钓点。失败或无数据返回 []。

    - target_species：按目标鱼习性优先推荐匹配标点。
    - max_travel_minutes / max_distance_km：按用户可接受车程过滤。
    - 保护区（可能禁钓）内的点位会被排除。

    返回元素：{name, spot_type, reason, lat, lon, distance_km}
    """
    # 车程 → 搜索半径（道路距离约等于直线距离的 1.2 倍，留余量）
    if max_distance_km:
        radius_m = max_distance_km * 1000 * 1.2
    elif max_travel_minutes:
        radius_m = (max_travel_minutes / 60) * 30 * 1000 * 1.2  # 按市区 30km/h 估算

    if lat is None or lon is None:
        if not place:
            return []
        loc = geo.lookup_location(place)
        if not loc or not loc.get("lat") or not loc.get("lon"):
            return []
        lat, lon = float(loc["lat"]), float(loc["lon"])

    ways: list[dict] = []
    protected: list[list[tuple[float, float]]] = []
    try:
        ways, protected = _query_overpass(lat, lon, radius_m)
    except Exception:  # noqa: BLE001
        ways, protected = [], []

    spots: list[dict] = []
    river_ways: list[dict] = []
    for w in ways:
        tags = w.get("tags") or {}
        name = tags.get("name") or "附近水域"
        wtype = tags.get("waterway") or tags.get("natural") or ""
        g = w.get("geometry") or []
        glatlon = [(p["lat"], p["lon"]) for p in g] if g else []
        if len(glatlon) < 4:
            continue
        if wtype in ("river", "stream"):
            river_ways.append(w)
            for blat, blon in find_bends(glatlon):
                glat, glon = wgs84_to_gcj02(blat, blon)
                spots.append(
                    {
                        "name": name,
                        "spot_type": "回水湾",
                        "reason": _BEND_REASON,
                        "lat": glat,
                        "lon": glon,
                        "distance_km": round(_haversine((lat, lon), (blat, blon)) / 1000, 1),
                        "priority": 0,
                    }
                )
        elif wtype == "water":
            nlat, nlon = _nearest(glatlon, (lat, lon))
            glat, glon = wgs84_to_gcj02(nlat, nlon)
            spots.append(
                {
                    "name": name,
                    "spot_type": "近岸",
                    "reason": "湖库近岸水草多、溶氧好，鱼爱贴边，背风处更佳",
                    "lat": glat,
                    "lon": glon,
                    "distance_km": round(_haversine((lat, lon), (nlat, nlon)) / 1000, 1),
                    "priority": 3,
                }
            )

    for clat, clon in find_confluences(river_ways):
        glat, glon = wgs84_to_gcj02(clat, clon)
        spots.append(
            {
                "name": "水道交汇处",
                "spot_type": "入水口",
                "reason": _CONFLUENCE_REASON,
                "lat": glat,
                "lon": glon,
                "distance_km": round(_haversine((lat, lon), (clat, clon)) / 1000, 1),
                "priority": 0,
            }
        )

    # 2) 高德 POI：钓场 + 命名水域（国内命名更全，补 OSM 短板）
    for poi in _amap_pois(lat, lon, radius_m, "垂钓", limit=3, type_filter="垂钓"):
        spots.append(
            {
                "name": poi["name"],
                "spot_type": "钓场",
                "reason": "垂钓园，鱼情和管理相对稳定，适合新手练手",
                "lat": poi["lat"],
                "lon": poi["lon"],
                "distance_km": round(_haversine((lat, lon), (poi["lat"], poi["lon"])) / 1000, 1),
                "priority": 1,
            }
        )
    for poi in _amap_pois(lat, lon, radius_m, "水库|湖泊|河流", limit=3):
        spots.append(
            {
                "name": poi["name"],
                "spot_type": "水域",
                "reason": "周边水域，到现场优先找入水口、回水湾、背风岸",
                "lat": poi["lat"],
                "lon": poi["lon"],
                "distance_km": round(_haversine((lat, lon), (poi["lat"], poi["lon"])) / 1000, 1),
                "priority": 2,
            }
        )

    # 鱼种习性匹配：匹配目标鱼偏好标点的候选优先推荐，并改写原因
    species_spots = (get_species(target_species) or {}).get("spots") or []
    if species_spots:
        for s in spots:
            if _species_prefers(species_spots, s["spot_type"]):
                s["priority"] = max(0, s["priority"] - 1)
                s["reason"] = f"适合打{target_species}：{s['reason']}"

    # 去重（按坐标近似）并按（优先级, 距离）排序
    seen: set[tuple[float, float]] = set()
    unique: list[dict] = []
    for s in sorted(spots, key=lambda x: (x["priority"], x["distance_km"])):
        key = (round(s["lat"], 3), round(s["lon"], 3))
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    # 车程/距离过滤：不推荐超出用户可接受范围的点位
    if max_distance_km:
        unique = [s for s in unique if s["distance_km"] <= max_distance_km * 1.2]
    elif max_travel_minutes:
        max_km = (max_travel_minutes / 60) * 30 * 1.2
        unique = [s for s in unique if s["distance_km"] <= max_km]

    # 保护区过滤（P0：不推荐禁钓区域）
    if protected:
        unique = [
            s for s in unique
            if not any(_point_in_polygon((s["lat"], s["lon"]), p) for p in protected)
        ]

    for s in unique:
        s.pop("priority", None)
    return unique[:limit]
