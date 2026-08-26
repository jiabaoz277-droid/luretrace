"""水域标点分析测试：几何启发（回水湾）+ 降级 + 对话接入。"""
import math

from app.services import agent, waters
from app.services.waters import (
    _haversine,
    _resample,
    find_bends,
    find_confluences,
    wgs84_to_gcj02,
)


def _straight_then_bend_geometry() -> list[tuple[float, float]]:
    """构造一条先东行 1km、再北转 1km 的直角河道（拐点约在 30.0,120.0104）。"""
    # 纬度 30 度处，1km 经度差 ≈ 0.0104 度；1km 纬度差 ≈ 0.009 度
    dlon = 0.0104
    dlat = 0.009
    geo = []
    for i in range(21):
        geo.append((30.0, 120.0 + dlon * i / 20))
    for i in range(1, 21):
        geo.append((30.0 + dlat * i / 20, 120.0 + dlon))
    return geo


def test_resample_keeps_length_roughly():
    pts = [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)]
    out = _resample(pts, 60.0)
    assert out[0] == pts[0]
    assert out[-1] == pts[-1]
    assert len(out) >= 3


def test_find_bends_detects_right_angle():
    geo = _straight_then_bend_geometry()
    bends = find_bends(geo)
    assert len(bends) >= 1
    # 拐点应落在拐角附近（约 30.0, 120.0104）
    blat, blon = bends[0]
    assert abs(blat - 30.0) < 0.002
    assert abs(blon - 120.0104) < 0.002


def test_find_bends_straight_river_returns_empty():
    geo = [(30.0, 120.0 + i * 0.0005) for i in range(100)]
    assert find_bends(geo) == []


def test_haversine():
    # 赤道上经度差 1 度 ≈ 111.32 km
    d = _haversine((0.0, 0.0), (0.0, 1.0))
    assert 110000 < d < 112000


def test_wgs84_to_gcj02_offsets_china():
    lat, lon = 29.79744, 119.68504  # 桐庐（中国境内）
    glat, glon = wgs84_to_gcj02(lat, lon)
    assert (glat, glon) != (lat, lon)  # 国内应有偏移
    d = _haversine((lat, lon), (glat, glon))
    assert 100 < d < 1000  # 偏移通常在几百米量级


def test_wgs84_to_gcj02_keeps_overseas():
    assert wgs84_to_gcj02(40.0, -74.0) == (40.0, -74.0)  # 境外不变


def test_find_confluences_near_endpoints():
    # 两条“河”端点相距很近 → 应识别为汇口
    ways = [
        {"geometry": [{"lat": 30.0, "lon": 120.0}, {"lat": 30.001, "lon": 120.0}]},
        {"geometry": [{"lat": 30.0005, "lon": 120.0}, {"lat": 30.002, "lon": 120.0}]},
    ]
    out = find_confluences(ways)
    assert len(out) >= 1


def test_find_spots_returns_empty_on_no_data(monkeypatch):
    monkeypatch.setattr(waters, "_query_overpass", lambda *a, **k: [])
    monkeypatch.setattr(waters, "_amap_pois", lambda *a, **k: [])
    assert waters.find_spots(place="杭州") == []


def test_find_spots_includes_amap_pois(monkeypatch):
    monkeypatch.setattr(waters, "_query_overpass", lambda *a, **k: [])

    def fake_amap(lat, lon, r, kw, limit=3, type_filter=None):
        if kw == "垂钓":
            return [{"name": "牛牛钓鱼场", "type": "垂钓园", "lat": 29.775, "lon": 119.666}]
        return [{"name": "溪旁水库", "type": "湖泊", "lat": 29.7728, "lon": 119.7233}]

    monkeypatch.setattr(waters, "_amap_pois", fake_amap)
    monkeypatch.setattr(
        waters.geo, "lookup_location", lambda *a, **k: {"name": "桐庐", "lat": 29.797, "lon": 119.685}
    )
    spots = waters.find_spots(place="桐庐", limit=3)
    assert spots
    assert spots[0]["spot_type"] == "钓场"  # 钓场优先于水域
    assert spots[0]["name"] == "牛牛钓鱼场"
    types = {s["spot_type"] for s in spots}
    assert "水域" in types


def test_find_spots_with_mock_river(monkeypatch):
    # 造一条带直角拐弯的河，绕过真实网络
    geo = _straight_then_bend_geometry()
    way = {
        "type": "way",
        "tags": {"waterway": "river", "name": "测试河"},
        "geometry": [{"lat": lat, "lon": lon} for lat, lon in geo],
    }
    monkeypatch.setattr(waters, "_query_overpass", lambda *a, **k: ([way], []))
    monkeypatch.setattr(waters, "_amap_pois", lambda *a, **k: [])
    monkeypatch.setattr(
        waters.geo,
        "lookup_location",
        lambda *a, **k: {"name": "杭州", "lat": 30.0, "lon": 120.0},
    )
    spots = waters.find_spots(place="杭州")
    assert spots, "应能分析出候选钓点"
    assert spots[0]["spot_type"] == "回水湾"
    assert spots[0]["name"] == "测试河"
    assert "distance_km" in spots[0]


def test_choose_place_flow_returns_spots(monkeypatch):
    geo = _straight_then_bend_geometry()
    way = {
        "type": "way",
        "tags": {"waterway": "river", "name": "富春江"},
        "geometry": [{"lat": lat, "lon": lon} for lat, lon in geo],
    }
    monkeypatch.setattr(waters, "_query_overpass", lambda *a, **k: ([way], []))
    monkeypatch.setattr(waters, "_amap_pois", lambda *a, **k: [])
    monkeypatch.setattr(
        waters.geo,
        "lookup_location",
        lambda *a, **k: {"name": "杭州", "lat": 30.0, "lon": 120.0},
    )
    r = agent.handle("杭州哪里好钓", None)
    assert "回水湾" in r["reply"]
    assert "富春江" in r["reply"]


def test_choose_place_asks_location_when_missing():
    r = agent.handle("哪里好钓", None)
    assert r["type"] == "clarify"
    assert r["missing"] == ["location"]


def test_choose_place_uses_context_coords(monkeypatch):
    called: dict = {}

    def fake_find_spots(place=None, lat=None, lon=None, radius_m=5000.0, limit=3,
                        target_species=None, max_travel_minutes=None, max_distance_km=None):
        called["lat"] = lat
        called["lon"] = lon
        called["species"] = target_species
        return []

    monkeypatch.setattr(waters, "find_spots", fake_find_spots)
    agent.prepare("哪里好钓", None, context={"lat": 30.0, "lon": 120.0})
    assert called["lat"] == 30.0  # 精确定位应被使用
    assert called["lon"] == 120.0


def test_species_prefers_spot_type():
    """鱼种标点匹配：翘嘴偏好湾口/入水口，鲫鱼偏好近岸浅滩。"""
    from app.services.waters import _species_prefers

    assert _species_prefers(["湾口", "深浅交界", "入水口"], "回水湾")
    assert _species_prefers(["湾口", "深浅交界", "入水口"], "入水口")
    assert _species_prefers(["浅滩", "水草边", "缓流区"], "近岸")
    assert not _species_prefers(["水面开阔区", "下风处"], "回水湾")
