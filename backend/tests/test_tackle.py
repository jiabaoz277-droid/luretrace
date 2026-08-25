"""钓具解析与决策联动测试。"""
from app.schemas.chat import FishingContext
from app.schemas.profile import ProfileData
from app.services import tackle
from app.services.decision import build_plan
from app.services.weather import get_hourly


def test_parse_rod_action():
    assert tackle.parse_rod_action(["ML调路亚竿"]) == "ML"
    assert tackle.parse_rod_action(["马口竿"]) == "UL"
    assert tackle.parse_rod_action(["7尺MH路亚竿"]) == "MH"
    assert tackle.parse_rod_action([]) is None


def test_weight_range():
    assert tackle.weight_range_for("ML") == (3, 12)
    assert tackle.weight_range_for("UL") == (0.5, 5)
    assert tackle.weight_range_for(None) is None


def test_parse_weight():
    assert tackle.parse_weight("7–10g") == (7, 10)
    assert tackle.parse_weight("3g") == (3, 3)
    assert tackle.parse_weight("微物") is None


def _ctx(**kw) -> FishingContext:
    base = dict(
        location="杭州",
        time_label="8月26日 05:00–09:00",
        start_iso="2026-08-26T05:00:00",
        end_iso="2026-08-26T09:00:00",
        target_species="翘嘴",
    )
    base.update(kw)
    return FishingContext(**base)


def test_rod_action_in_factors():
    profile = ProfileData(rods=["ML调路亚竿"])
    plan = build_plan(_ctx(), get_hourly("杭州"), [], profile=profile)
    assert any("ML 竿" in f for f in plan.factors)


def test_rod_too_soft_risk():
    # 翘嘴推荐 7-10g，UL 竿范围 0.5-5g → 应提示超范围
    profile = ProfileData(rods=["UL马口竿"])
    plan = build_plan(_ctx(), get_hourly("杭州"), [], profile=profile)
    assert any("超出" in r for r in plan.risks)
