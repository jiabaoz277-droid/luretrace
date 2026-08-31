"""提示词管理后台接口测试（X-Admin-Token 鉴权 + 运行时覆盖生效）。"""
import pytest

from app.core.config import settings
from app.main import app
from app.services import prompts

ADMIN = "test-admin-token"


@pytest.fixture(autouse=True)
def _admin_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", ADMIN)
    prompts._cache.clear()
    yield
    prompts._cache.clear()


def _h() -> dict:
    return {"X-Admin-Token": ADMIN}


def test_admin_requires_token(client):
    r = client.get("/api/v1/admin/prompts")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_admin_token"


def test_admin_cookie_login_and_logout(client):
    login = client.post("/api/v1/admin/prompts/login", json={"token": ADMIN})
    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"]
    assert client.get("/api/v1/admin/prompts").status_code == 200
    assert client.post("/api/v1/admin/prompts/logout").status_code == 204
    assert client.get("/api/v1/admin/prompts").status_code == 401


def test_admin_list(client):
    r = client.get("/api/v1/admin/prompts", headers=_h())
    assert r.status_code == 200
    items = r.json()["items"]
    keys = {it["key"] for it in items}
    assert len(items) >= 14
    assert {"reply_system", "compliance_note", "clarify_location", "safety_rules"} <= keys


def test_admin_update_and_reset(client):
    h = _h()
    r = client.put("/api/v1/admin/prompts/clarify_location", json={"value": "你在哪个城市？"}, headers=h)
    assert r.status_code == 200
    assert r.json()["value"] == "你在哪个城市？"
    assert prompts.get_text("clarify_location") == "你在哪个城市？"

    r = client.post("/api/v1/admin/prompts/clarify_location/reset", headers=h)
    assert r.status_code == 200
    default = prompts.DEFAULT_PROMPTS["clarify_location"]["default"]
    assert prompts.get_text("clarify_location") == default


def test_runtime_uses_override(client):
    from app.services import llm

    client.put("/api/v1/admin/prompts/clarify_species", json={"value": "打什么目标鱼？"}, headers=_h())
    assert llm.reply_for_clarify("target_species") == "打什么目标鱼？"
    client.post("/api/v1/admin/prompts/clarify_species/reset", headers=_h())
    assert llm.reply_for_clarify("target_species") != "打什么目标鱼？"


def test_unknown_key_404(client):
    r = client.put("/api/v1/admin/prompts/not_exist", json={"value": "x"}, headers=_h())
    assert r.status_code == 404
