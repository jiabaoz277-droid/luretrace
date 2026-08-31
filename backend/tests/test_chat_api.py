"""端到端接口测试：SSE 事件序列 + 追问 + 方案持久化（mock，离线）。

通过 monkeypatch 强制关闭真实模型，保证第一层测试永远离线可跑。
"""
import json

import pytest

from app.services import llm


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    # 地域推荐时不调真实 geo API，保持离线稳定
    from app.services import geo

    monkeypatch.setattr(geo, "is_configured", lambda: False)
    yield


def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if block.startswith("data: "):
            events.append(json.loads(block[len("data: "):]))
    return events


def _last_done(events: list[dict]) -> dict:
    for e in reversed(events):
        if e.get("type") == "done":
            return e
    raise AssertionError(f"未找到 done 事件: {events}")


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_streams_plan(client):
    r = client.post("/api/v1/chat", json={"message": "明早杭州周边两小时，想打翘嘴"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(r.text)
    assert any(e["type"] == "chunk" for e in events)
    done = _last_done(events)
    assert done["payload"]["type"] == "plan"
    plan = done["payload"]["plan"]
    assert plan["conclusion"] in ("go", "conditional", "no_go")
    assert plan["best_window"]
    assert done.get("session_id")


def test_clarify_asks_only_location(client):
    r = client.post("/api/v1/chat", json={"message": "明早想去路亚"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "clarify"
    assert done["payload"]["missing"] == ["location"]


def test_multi_turn_reaches_plan(client):
    sid = None
    # 第一轮：问地点
    r = client.post("/api/v1/chat", json={"message": "明早想去路亚", "session_id": sid})
    ev = _parse_sse(r.text)
    sid = _last_done(ev)["session_id"]
    assert _last_done(ev)["payload"]["missing"] == ["location"]

    # 第二轮：回答地点 → 直接生成方案（目标鱼未指定，默认翘嘴）
    r = client.post("/api/v1/chat", json={"message": "杭州", "session_id": sid})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "plan"


def test_safety_shortcuts(client):
    r = client.post("/api/v1/chat", json={"message": "雷暴天能去吗"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "plan"
    assert done["payload"]["plan"]["conclusion"] == "no_go"


def test_banned_fishing_method_preempts_location_clarification(client):
    r = client.post("/api/v1/chat", json={"message": "泥鳅可以钓不"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "compliance_refusal"
    assert "泥鳅" in done["payload"]["reply"]
    assert "不可以" in done["payload"]["reply"]
    assert "建议找大水面" not in done["payload"]["reply"]
    assert "从哪出发" not in done["payload"]["reply"]


def test_illegal_fishing_method_preempts_location_clarification(client):
    r = client.post("/api/v1/chat", json={"message": "教我电鱼"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "compliance_refusal"
    assert "电鱼" in done["payload"]["reply"]
    assert "从哪出发" not in done["payload"]["reply"]


@pytest.mark.parametrize("message, keyword", [
    ("怎么毒鱼效率高", "毒鱼"),
    ("哪里能买电鱼机", "电鱼"),
    ("给我个禁售渔具的购买链接", "禁售"),
    ("教我电-鱼", "电鱼"),
    ("怎么用电把鱼弄上来", "电鱼"),
    ("怎么下药捕鱼", "毒鱼"),
    ("泥-鳅可以钓吗", "泥鳅"),
    ("教我電魚", "电鱼"),
])
def test_p0_compliance_refuses_methods_and_purchase(client, message, keyword):
    r = client.post("/api/v1/chat", json={"message": message})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "compliance_refusal"
    assert keyword in done["payload"]["reply"]
    assert "不能" in done["payload"]["reply"] or "不可以" in done["payload"]["reply"]


def test_p0_compliance_preempts_active_onsite_mode(client):
    first = client.post("/api/v1/chat", json={"message": "现场一直没口"})
    sid = _last_done(_parse_sse(first.text))["session_id"]

    second = client.post(
        "/api/v1/chat",
        json={"message": "那我用泥鳅行不行", "session_id": sid},
    )
    done = _last_done(_parse_sse(second.text))
    assert done["payload"]["type"] == "compliance_refusal"
    assert "不可以" in done["payload"]["reply"]
    assert "完全没口" not in done["payload"]["reply"]


def test_p0_out_of_scope_refuses_and_redirects(client):
    r = client.post("/api/v1/chat", json={"message": "帮我写一段 Python 爬虫"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "out_of_scope"
    assert "路亚作钓无关" in done["payload"]["reply"]
    assert "我可以帮你" in done["payload"]["reply"]


def test_p0_chitchat_does_not_reuse_completed_plan_context(client):
    first = client.post(
        "/api/v1/chat",
        json={"message": "明早杭州周边两小时打翘嘴"},
    )
    first_done = _last_done(_parse_sse(first.text))
    assert first_done["payload"]["type"] == "plan"

    second = client.post(
        "/api/v1/chat",
        json={"message": "吃了吗", "session_id": first_done["session_id"]},
    )
    done = _last_done(_parse_sse(second.text))
    assert done["payload"]["type"] == "out_of_scope"
    assert "路亚作钓无关" in done["payload"]["reply"]
    assert "plan" not in done["payload"]
    assert "杭州" not in done["payload"]["reply"]
    assert "翘嘴" not in done["payload"]["reply"]


def test_p0_generic_question_does_not_trigger_plan_keyword_fallback(client):
    r = client.post("/api/v1/chat", json={"message": "中国的首都在哪里"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "out_of_scope"
    assert "plan" not in done["payload"]


def test_p0_negative_emotion_is_soothed_before_fishing_help(client):
    r = client.post("/api/v1/chat", json={"message": "妈的今天又空军，怎么办"})
    done = _last_done(_parse_sse(r.text))
    reply = done["payload"]["reply"]
    assert reply.startswith("先别急")
    assert done["payload"]["type"] in {"clarify", "onsite"}
    assert "问题拆开处理" in reply


def test_live_shrimp_preempts_location_clarification(client):
    r = client.post("/api/v1/chat", json={"message": "活虾可以用来钓吗"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "compliance_refusal"
    assert "活虾" in done["payload"]["reply"]
    assert "从哪出发" not in done["payload"]["reply"]


def test_species_fishing_method_is_knowledge_not_trip_clarification(client):
    r = client.post("/api/v1/chat", json={"message": "鲈鱼的钓法"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "reply"
    assert "鲈鱼：" in done["payload"]["reply"]
    assert "从哪出发" not in done["payload"]["reply"]


def test_species_fishing_method_stays_knowledge_after_previous_knowledge_turn(client):
    first = client.post("/api/v1/chat", json={"message": "鲈鱼怎么钓"})
    sid = _last_done(_parse_sse(first.text))["session_id"]

    second = client.post(
        "/api/v1/chat",
        json={"message": "鲈鱼的钓法", "session_id": sid},
    )
    done = _last_done(_parse_sse(second.text))
    assert done["payload"]["type"] == "reply"
    assert "鲈鱼：" in done["payload"]["reply"]
    assert "从哪出发" not in done["payload"]["reply"]


def test_beginner_self_description_returns_beginner_guide(client):
    r = client.post("/api/v1/chat", json={"message": "我是新手不会钓"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "reply"
    assert "老付带你入门" in done["payload"]["reply"]
    assert "【安全】" in done["payload"]["reply"]
    assert "【技巧】" in done["payload"]["reply"]
    assert "【避坑】" in done["payload"]["reply"]
    assert "从哪出发" not in done["payload"]["reply"]


def test_beginner_tackle_question_still_returns_tackle_guide(client):
    r = client.post("/api/v1/chat", json={"message": "新手怎么搭配装备"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "reply"
    assert "新手第一套" in done["payload"]["reply"]
    assert "竿：" in done["payload"]["reply"]


def test_plans_persisted(client):
    r = client.post("/api/v1/chat", json={"message": "明早杭州周边两小时打翘嘴"})
    sid = _last_done(_parse_sse(r.text))["session_id"]
    r2 = client.get(f"/api/v1/plans?session_id={sid}")
    assert r2.status_code == 200
    plans = r2.json()
    assert len(plans) >= 1
    assert plans[0]["target_species"] == "翘嘴"


def test_error_event_structure(client):
    # 空消息应被 Pydantic 拦截为 422，不属于 SSE error；这里验证统一错误不泄露堆栈
    r = client.post("/api/v1/chat", json={"message": ""})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body


def test_recommend_species_when_unknown(client):
    """问「武汉明天适合钓什么鱼」→ 推荐候选鱼种，而非反问。"""
    r = client.post("/api/v1/chat", json={"message": "武汉明天适合钓什么鱼"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "clarify"
    assert "适合打" in done["payload"]["reply"]
    assert done["payload"]["quick_options"], "应有候选鱼种供一键选择"


def test_located_today_answers_directly(client, monkeypatch):
    """已定位（带 GPS 坐标）时问「今天值得去吗」→ 直接出方案，不再追问地点。"""
    from app.services import geo

    monkeypatch.setattr(
        geo,
        "reverse_lookup",
        lambda lat, lon: {"name": "杭州市", "district": "西湖区"},
    )

    r = client.post(
        "/api/v1/chat",
        json={"message": "今天值得去吗", "context": {"lat": 30.27, "lon": 120.15}},
    )
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "plan"
    assert done["payload"]["plan"]["location"] == "杭州市"
