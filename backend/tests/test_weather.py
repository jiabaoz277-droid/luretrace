"""天气查询：真实数据优先，mock 降级。"""
import pytest

from app.services import weather
from app.services import geo


def test_mock_fallback_when_no_key(monkeypatch):
    monkeypatch.setattr(geo, "is_configured", lambda: False)
    w = weather.get_hourly("杭州")
    assert w["meta"]["mock"] is True
    assert w["meta"]["source"] == "mock"
    assert len(w["hourly"]) == 24
    assert w["sunrise"] and w["sunset"]


def test_mock_fallback_when_no_location():
    w = weather.get_hourly(None)
    assert w["meta"]["mock"] is True


def test_real_weather_smoke():
    if not geo.is_configured():
        pytest.skip("未配置 QWEATHER_KEY，跳过真实天气冒烟")
    w = weather.get_hourly("杭州")
    assert w["meta"]["mock"] is False
    assert w["meta"]["source"] == "qweather"
    assert len(w["hourly"]) == 24
    assert any(h["pressure"] > 0 for h in w["hourly"])
    assert w["sunrise"] and w["sunset"]
