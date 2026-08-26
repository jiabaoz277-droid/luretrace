"""战报字段解析测试。"""
from app.services import agent as agent_mod


def test_report_parses_extra_fields():
    assert agent_mod._extract_lure("用了亮片和米诺") == "亮片、米诺"
    assert agent_mod._extract_length_weight("钓了条3斤的") == "3斤"
    assert agent_mod._extract_water_color("水很浑") == "浑"
    assert agent_mod._extract_flow("急流") == "急流"


def test_report_flow_parses_lure_and_water():
    # 战报流两步：先触发复盘，再回结果（同一 session）
    agent_mod._sessions.clear()
    r1 = agent_mod.handle("记一下战报", None)
    assert r1["type"] == "clarify"
    r2 = agent_mod.handle("空军，用的亮片，水很浑", r1["session_id"])
    assert r2["type"] == "report"
    assert r2["report"]["lure"] == "亮片"
    assert r2["report"]["water_color"] == "浑"
