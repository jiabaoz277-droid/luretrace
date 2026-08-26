"""多日出钓预报测试（mock，离线）。"""
from app.services import forecast, intent
from app.services.decision import hourly_fish_scores
from app.services.weather import _daily_mock


def test_intent_detects_forecast():
    r = intent.detect_intent("未来几天哪天适合钓鱼")
    assert r.primary_intent == "PLAN_TRIP"
    assert "FORECAST" in r.secondary_intents
    r2 = intent.detect_intent("这周末哪天好")
    assert r2.primary_intent == "PLAN_TRIP"
    assert "FORECAST" in r2.secondary_intents


def test_score_day_blocking_weather():
    score, _ = forecast._score_day(
        {"condition": "雷阵雨", "precip_prob": 80, "wind_scale": 5, "temp_max": 30, "temp_min": 22}
    )
    assert score < 50  # 雷暴应大幅降分


def test_score_day_good_weather():
    score, _ = forecast._score_day(
        {"condition": "晴", "precip_prob": 5, "wind_scale": 2, "temp_max": 28, "temp_min": 20}
    )
    assert score >= 75


def test_build_forecast_sorts(monkeypatch):
    monkeypatch.setattr(forecast, "get_daily_forecast", lambda loc, days=7: _daily_mock(loc, days))
    data = forecast.build_forecast("杭州", days=7)
    assert len(data["results"]) == 7
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)  # 降序排列
    assert data["season_tip"]  # 应有季节提示


def test_forecast_reply(monkeypatch):
    monkeypatch.setattr(forecast, "get_daily_forecast", lambda loc, days=7: _daily_mock(loc, days))
    reply = forecast.forecast_reply("杭州")
    assert "评分" in reply
    assert "最佳窗口" in reply


def test_hourly_fish_scores():
    hourly = [
        {"time": "2026-08-26T06:00+08:00", "temp": 27, "precip_prob": 0, "wind_scale": 2, "pressure": 1008, "pressure_trend": "缓升", "condition": "晴"},
        {"time": "2026-08-26T07:00+08:00", "temp": 30, "precip_prob": 80, "wind_scale": 5, "pressure": 995, "pressure_trend": "下降", "condition": "雷阵雨"},
    ]
    scores = hourly_fish_scores(hourly)
    assert len(scores) == 2
    assert scores[0]["score"] > scores[1]["score"]  # 好天气应高于雷暴
    assert scores[0]["hour"] == "06"
    assert 0 <= scores[1]["score"] <= 100
