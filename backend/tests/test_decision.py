"""决策引擎测试：方案完整性 + 安全优先 + 分数约束。"""
from app.schemas.chat import FishingContext
from app.services.decision import build_plan
from app.services.weather import get_hourly


def _ctx(**kw) -> FishingContext:
    base = dict(
        location="杭州",
        time_label="8月26日 05:00–09:00",
        start_iso="2026-08-26T05:00:00",
        end_iso="2026-08-26T09:00:00",
        target_species="翘嘴",
        travel_radius="2小时",
    )
    base.update(kw)
    return FishingContext(**base)


def test_plan_contains_required_fields():
    plan = build_plan(_ctx(), get_hourly("杭州"), [])
    d = plan.plan_detail
    # PRD FR-03：至少含时间、标点、水层、拟饵、手法、调整条件中的 5 项
    present = sum(
        1 for v in [d.spot_type, d.water_layer, d.primary_lure, d.weight_color, d.action, d.adjust_condition] if v
    )
    assert present >= 5
    assert plan.best_window is not None
    assert 0 <= plan.score <= 100
    assert plan.factors, "分数必须附带主要构成因素"
    assert plan.conclusion in ("go", "conditional", "no_go")


def test_safety_overrides_fishing():
    plan = build_plan(_ctx(), get_hourly("杭州"), ["雷暴"])
    assert plan.conclusion == "no_go"
    assert plan.safety, "高风险必须输出安全提示"
    assert plan.score == 0


def test_strong_wind_blocks():
    plan = build_plan(_ctx(), get_hourly("杭州"), ["大风"])
    assert plan.conclusion == "no_go"


def test_missing_location_lowers_confidence():
    plan = build_plan(_ctx(location=None), get_hourly(None), [])
    assert plan.confidence == "low"
    assert any("位置" in r for r in plan.risks)


def test_default_species():
    plan = build_plan(_ctx(target_species=None), get_hourly("杭州"), [])
    assert plan.target_species == "翘嘴"
    assert any("未指定对象鱼" in r for r in plan.risks)


def test_today_afternoon_skips_past_morning():
    """午后问“今天”：只推荐当天剩余的傍晚窗口，不推荐已过去的清晨。"""
    from datetime import datetime

    now = datetime(2026, 8, 27, 11, 0)
    ctx = _ctx(
        time_label="8月27日 11:00–22:00",
        start_iso="2026-08-27T11:00:00+08:00",
        end_iso="2026-08-27T22:00:00+08:00",
    )
    plan = build_plan(ctx, get_hourly("杭州", target_date=now), [], now=now)
    assert plan.best_window == "16:00–18:00"


def test_today_past_explicit_window_tells_reschedule():
    """明确问今天清晨但已过点：明确提示改期，不静默推荐过去的时间。"""
    from datetime import datetime

    now = datetime(2026, 8, 27, 11, 0)
    ctx = _ctx(
        time_label="8月27日 05:00–09:00",
        start_iso="2026-08-27T05:00:00+08:00",
        end_iso="2026-08-27T09:00:00+08:00",
    )
    plan = build_plan(ctx, get_hourly("杭州", target_date=now), [], now=now)
    assert any("已过" in s for s in plan.safety)
