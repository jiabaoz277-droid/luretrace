"""第 2 阶段测试：排障规则、装备偏好联动、战报与复盘（mock，离线）。"""
import json

import pytest

from app.core import db
from app.schemas.chat import FishingContext
from app.schemas.profile import ProfileData
from app.services import llm, onsite, profile as profile_service
from app.services.decision import build_plan
from app.services.weather import get_hourly


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    yield


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


# ---------- 排障 ----------

def test_onsite_classify():
    assert onsite.classify_signal("完全没口") == "no_sign"
    assert onsite.classify_signal("有炸水但打不到") == "chasing"
    assert onsite.classify_signal("有跟口不咬") == "follow_not_bite"
    assert onsite.classify_signal("频繁挂底") == "snag"
    assert onsite.classify_signal("老跑鱼") == "lost_fish"


def test_onsite_steps_structure():
    for signal in ("chasing", "no_sign", "follow_not_bite", "snag", "lost_fish"):
        steps = onsite.build_steps(signal)
        assert len(steps) == 3
        for s in steps:
            assert s["action"] and s["duration"]
        assert steps[0]["upgrade"], "第一步必须有升级条件"


# ---------- 装备偏好 ----------

def test_profile_save_and_get():
    with db.get_session() as s:
        saved = profile_service.save_profile(
            s,
            ProfileData(lures=["7g亮片", "米诺"], max_travel_radius="40分钟", constraints=["不夜钓"]),
        )
        assert saved.lures == ["7g亮片", "米诺"]
        got = profile_service.get_profile(s)
        assert got.max_travel_radius == "40分钟"
        assert "不夜钓" in got.constraints


def test_decision_uses_profile_lures():
    profile = ProfileData(lures=["7g亮片", "米诺"])
    plan = build_plan(_ctx(), get_hourly("杭州"), [], profile=profile)
    assert plan.plan_detail.primary_lure == "7g亮片"
    assert plan.plan_detail.backup_lure == "亮片"  # 备选为鱼种推荐拟饵
    assert any("常用拟饵" in f for f in plan.factors)


def test_decision_uses_profile_radius_when_absent():
    profile = ProfileData(max_travel_radius="40分钟")
    plan = build_plan(_ctx(), get_hourly("杭州"), [], profile=profile)
    assert plan.travel_radius == "40分钟"


def test_user_radius_overrides_profile():
    profile = ProfileData(max_travel_radius="40分钟")
    plan = build_plan(_ctx(travel_radius="2小时"), get_hourly("杭州"), [], profile=profile)
    assert plan.travel_radius == "2小时"  # 用户本轮覆盖


def test_decision_no_night_fishing():
    profile = ProfileData(constraints=["不夜钓"])
    plan = build_plan(_ctx(), get_hourly("杭州"), [], profile=profile)
    # 晨昏窗口，不触发夜间提示；只验证不报错
    assert plan.conclusion in ("go", "conditional", "no_go")


# ---------- 战报/复盘（API 端到端） ----------

def _parse_sse(text: str) -> list[dict]:
    return [json.loads(b[6:]) for b in text.split("\n\n") if b.strip().startswith("data: ")]


def _done(events):
    for e in reversed(events):
        if e.get("type") == "done":
            return e["payload"]
    raise AssertionError("无 done")


def test_onsite_flow(client):
    r = client.post("/api/v1/chat", json={"message": "到水边没口"})
    p = _done(_parse_sse(r.text))
    assert p["type"] == "clarify"
    assert "信号" in p["reply"]
    assert p["quick_options"]

    sid = _parse_sse(r.text)[-1]["session_id"]
    r2 = client.post("/api/v1/chat", json={"message": "完全没口", "session_id": sid})
    p2 = _done(_parse_sse(r2.text))
    assert p2["type"] == "onsite"
    assert len(p2["steps"]) == 3


def test_report_flow(client):
    r = client.post("/api/v1/chat", json={"message": "记一下今天的战报"})
    p = _done(_parse_sse(r.text))
    assert p["type"] == "clarify"
    assert p["quick_options"] == ["上鱼", "有口未中", "空军", "未出钓"]
    sid = _parse_sse(r.text)[-1]["session_id"]

    r2 = client.post("/api/v1/chat", json={"message": "空军", "session_id": sid})
    p2 = _done(_parse_sse(r2.text))
    assert p2["type"] == "report"
    assert p2["report"]["result_type"] == "skunked"
    assert "写入" in p2["reply"]

    # 未确认前 review_confirmed=False
    rid = p2["report"]["id"]
    r3 = client.post("/api/v1/chat", json={"message": "确认", "session_id": sid})
    p3 = _done(_parse_sse(r3.text))
    assert "已保存" in p3["reply"]

    r4 = client.get(f"/api/v1/reports?session_id={sid}")
    reps = r4.json()
    assert len(reps) == 1
    assert reps[0]["id"] == rid
    assert reps[0]["review_confirmed"] is True


def test_report_edit_delete(client):
    client.post("/api/v1/chat", json={"message": "记一下今天的战报"})
    # 直接通过接口创建一条也可；这里验证删除接口
    from app.core import auth
    from app.models.report import CatchReport

    uid = auth._user_id_for_code("TESTCODE")
    with db.get_session() as s:
        rep = CatchReport(session_id="abc", result_type="skunked", user_id=uid)
        s.add(rep)
        s.commit()
        rid = rep.id

    r = client.delete(f"/api/v1/reports/{rid}")
    assert r.status_code == 200
    r2 = client.get(f"/api/v1/reports/{rid}")
    assert r2.status_code == 404


def test_profile_api(client):
    r = client.put("/api/v1/profile", json={"lures": ["亮片"], "max_travel_radius": "30分钟"})
    assert r.status_code == 200
    assert r.json()["lures"] == ["亮片"]
    r2 = client.get("/api/v1/profile")
    assert r2.json()["max_travel_radius"] == "30分钟"
