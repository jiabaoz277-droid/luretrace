"""地理位置：正/逆地理编码（真实数据冒烟，无 Key 自动跳过）。"""
import pytest

from app.services import geo


def test_lookup_location_smoke():
    if not geo.is_configured():
        pytest.skip("未配置 QWEATHER_KEY/HOST")
    place = geo.lookup_location("杭州")
    assert place is not None
    assert place["lat"] and place["lon"]


def test_reverse_lookup_smoke():
    if not geo.is_configured():
        pytest.skip("未配置 QWEATHER_KEY/HOST")
    # 杭州坐标
    place = geo.reverse_lookup(30.24603, 120.21079)
    assert place is not None
    assert place["name"]


def test_not_configured(monkeypatch):
    monkeypatch.setattr(geo, "is_configured", lambda: False)
    assert geo.lookup_location("杭州") is None
    assert geo.reverse_lookup(30.24, 120.21) is None
