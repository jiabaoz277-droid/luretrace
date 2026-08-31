"""后端稳定性修复的回归测试。"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from fastapi.testclient import TestClient

from app.core import auth, backup, db, rate_limit
from app.core.config import settings
from app.main import app
from app.services import agent, llm, weather


def test_conversation_survives_memory_cache_clear(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    monkeypatch.setattr(
        agent,
        "get_hourly",
        lambda location, now=None: weather._mock(location, now or datetime.now()),
    )

    first = agent.handle("明早杭州周边两小时打翘嘴", None)
    assert first["type"] == "plan"
    sid = first["session_id"]
    assert first["plan"].version == 1

    agent._sessions.clear()  # 模拟冷启动/切到另一实例
    second = agent.handle("明晚杭州周边两小时打翘嘴", sid)
    assert second["session_id"] == sid
    assert second["plan"].version == 2


def test_login_rate_limit(monkeypatch):
    monkeypatch.setattr(settings, "login_rate_limit", 2)
    monkeypatch.setattr(settings, "login_rate_window_seconds", 60)
    monkeypatch.setattr(settings, "login_block_seconds", 30)
    rate_limit.reset()
    client = TestClient(app)

    assert client.post("/api/v1/auth/login", json={"code": "wrong-1"}).status_code == 401
    blocked = client.post("/api/v1/auth/login", json={"code": "wrong-2"})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_login_rate_limit_ignores_spoofed_x_real_ip(monkeypatch):
    monkeypatch.setattr(settings, "login_rate_limit", 2)
    monkeypatch.setattr(settings, "login_rate_window_seconds", 60)
    monkeypatch.setattr(settings, "login_block_seconds", 30)
    rate_limit.reset()
    client = TestClient(app)

    first = client.post(
        "/api/v1/auth/login", json={"code": "wrong-1"}, headers={"X-Real-IP": "203.0.113.1"}
    )
    second = client.post(
        "/api/v1/auth/login", json={"code": "wrong-2"}, headers={"X-Real-IP": "203.0.113.2"}
    )
    assert first.status_code == 401
    assert second.status_code == 429


def test_action_rate_limit_window():
    rate_limit.reset()
    assert rate_limit.check_action("chat:test", limit=2, window_seconds=60) == 0
    assert rate_limit.check_action("chat:test", limit=2, window_seconds=60) == 0
    assert rate_limit.check_action("chat:test", limit=2, window_seconds=60) > 0


def test_spot_list_pagination(client):
    for index in range(3):
        client.post("/api/v1/spots", json={"name": f"钓点{index}"})
    response = client.get("/api/v1/spots?limit=1&offset=1")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["钓点1"]


def test_sqlite_backup_is_consistent(tmp_path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO sample(value) VALUES ('ok')")
        conn.commit()

    original = backup._LOCAL_FALLBACK
    target = tmp_path / "backup" / "app.db"
    backup._LOCAL_FALLBACK = target
    try:
        assert backup.backup_db(source) is True
        with sqlite3.connect(target) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("SELECT value FROM sample").fetchone()[0] == "ok"
    finally:
        backup._LOCAL_FALLBACK = original
