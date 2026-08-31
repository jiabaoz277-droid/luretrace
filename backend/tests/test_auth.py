"""登录与数据隔离测试（无真实模型，离线）。"""
import json

from fastapi.testclient import TestClient

from app.core import auth
from app.main import app


def test_health_requires_no_auth():
    c = TestClient(app)
    assert c.get("/api/v1/health").status_code == 200


def test_login_ok():
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"code": "TESTCODE"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "token" not in body
    assert body["user_id"] == auth._user_id_for_code("TESTCODE")
    assert body["expires_in"] > 0
    cookie = r.headers["set-cookie"]
    assert f"{auth.SESSION_COOKIE}=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert c.get("/api/v1/auth/session").json()["authenticated"] is True


def test_logout_clears_cookie():
    c = TestClient(app)
    assert c.post("/api/v1/auth/login", json={"code": "TESTCODE"}).status_code == 200
    assert c.post("/api/v1/auth/logout").status_code == 204
    assert c.get("/api/v1/auth/session").status_code == 401


def test_login_wrong_code():
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"code": "WRONG"})
    assert r.status_code == 401


def test_protected_requires_token():
    c = TestClient(app)
    assert c.get("/api/v1/spots").status_code == 401
    assert c.post("/api/v1/chat", json={"message": "明早杭州打翘嘴"}).status_code == 401


def test_invalid_token_rejected():
    c = TestClient(app, headers={"Authorization": "Bearer not-a-real-token"})
    assert c.get("/api/v1/insights").status_code == 401


def test_data_isolation_between_users():
    """A 用户看不到 B 用户的收藏和方案。"""
    ua = auth._user_id_for_code("CODEA")
    ub = auth._user_id_for_code("CODEB")
    ca = TestClient(app, headers={"Authorization": f"Bearer {auth.create_token(ua)}"})
    cb = TestClient(app, headers={"Authorization": f"Bearer {auth.create_token(ub)}"})

    # 收藏隔离
    ca.post("/api/v1/spots", json={"name": "富春江"})
    assert len(ca.get("/api/v1/spots").json()) == 1
    assert cb.get("/api/v1/spots").json() == []

    # 方案隔离：A 对话产生 session，B 用同一 session_id 查不到
    r = ca.post("/api/v1/chat", json={"message": "明早杭州周边两小时打翘嘴"})
    sid_a = None
    for block in r.text.split("\n\n"):
        if block.strip().startswith("data: "):
            ev = json.loads(block[len("data: "):])
            if ev.get("session_id"):
                sid_a = ev["session_id"]
    assert sid_a
    assert cb.get(f"/api/v1/plans?session_id={sid_a}").json() == []
    assert len(ca.get(f"/api/v1/plans?session_id={sid_a}").json()) >= 1
