"""第 3 阶段测试：收藏钓点、个性化统计、相似历史（mock，离线）。"""
import json

import pytest

from app.core import db
from app.models.report import CatchReport
from app.services import insights, llm
from app.services.agent import handle


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    yield


# ---------- 收藏钓点 ----------

def test_spots_api(client):
    r = client.post("/api/v1/spots", json={"name": "富春江", "location": "富春江"})
    assert r.status_code == 200
    assert r.json()["name"] == "富春江"
    sid = r.json()["id"]

    r2 = client.get("/api/v1/spots")
    assert len(r2.json()) == 1

    r3 = client.delete(f"/api/v1/spots/{sid}")
    assert r3.status_code == 200
    assert client.get("/api/v1/spots").json() == []


def test_favorite_dialog():
    r = handle("收藏富春江", None)
    assert "已收藏" in r["reply"]
    r2 = handle("我的收藏", r["session_id"])
    assert "富春江" in r2["reply"]


def test_favorite_dialog_empty():
    r = handle("我的收藏", None)
    assert "还没有收藏" in r["reply"]


# ---------- 个性化统计 ----------

def test_insights_compute():
    with db.get_session() as s:
        s.add(CatchReport(session_id="a", result_type="landed", species="翘嘴", count=2))
        s.add(CatchReport(session_id="b", result_type="skunked", species="鳜鱼"))
        s.commit()
        stats = insights.compute(s)
    assert stats["total"] == 2
    assert stats["result_dist"]["上鱼"] == 1
    assert stats["result_dist"]["空军"] == 1
    assert len(stats["top_species"]) == 2


def test_insight_dialog_empty():
    r = handle("我的规律", None)
    assert "还没有战报" in r["reply"]


def test_insight_dialog_with_data():
    with db.get_session() as s:
        s.add(CatchReport(session_id="a", result_type="landed", species="翘嘴"))
        s.commit()
    r = handle("我的规律", None)
    assert "1 次战报" in r["reply"]


# ---------- 相似历史 ----------

def test_similar_history_note():
    with db.get_session() as s:
        s.add(CatchReport(session_id="old", result_type="skunked", species="翘嘴"))
        s.commit()
    r = handle("明早杭州周边两小时打翘嘴", None)
    assert r["type"] == "plan"
    assert r["plan"].history_note
    assert "历史参考" in r["plan"].history_note
    assert "空军" in r["plan"].history_note


def test_similar_history_none():
    r = handle("明早杭州周边两小时打马口", None)
    assert r["plan"].history_note is None


# ---------- 接口 ----------

def test_insights_api(client):
    r = client.get("/api/v1/insights")
    assert r.status_code == 200
    assert "total" in r.json()
