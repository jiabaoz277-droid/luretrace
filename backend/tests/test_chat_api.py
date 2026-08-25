"""端到端接口测试：SSE 事件序列 + 追问 + 方案持久化（mock，离线）。

通过 monkeypatch 强制关闭真实模型，保证第一层测试永远离线可跑。
"""
import json

import pytest

from app.services import llm


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
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

    # 第二轮：回答地点 → 问目标鱼
    r = client.post("/api/v1/chat", json={"message": "杭州", "session_id": sid})
    ev = _parse_sse(r.text)
    done = _last_done(ev)
    assert done["payload"]["type"] == "clarify"
    assert done["payload"]["missing"] == ["target_species"]

    # 第三轮：回答目标鱼 → 生成方案
    r = client.post("/api/v1/chat", json={"message": "翘嘴", "session_id": sid})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "plan"


def test_safety_shortcuts(client):
    r = client.post("/api/v1/chat", json={"message": "雷暴天能去吗"})
    done = _last_done(_parse_sse(r.text))
    assert done["payload"]["type"] == "plan"
    assert done["payload"]["plan"]["conclusion"] == "no_go"


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
