"""知识库内容接入对话回复的回归测试（实操技巧 / 法规 / 常见误区）。"""
from app.services import agent, llm, onsite
from app.services.intent import detect_intent


def test_intent_detects_content_keywords():
    assert detect_intent("新手有什么误区").primary_intent == "KNOWLEDGE_QA"
    assert detect_intent("有哪些实操技巧").primary_intent == "KNOWLEDGE_QA"
    assert detect_intent("路亚入门注意什么").primary_intent == "KNOWLEDGE_QA"


def test_onsite_steps_include_tips():
    reply = onsite.steps_reply("snag")
    assert "挂底轻抖竿脱困" in reply  # 挂底专属技巧
    assert "保持安静" in reply  # 通用技巧
    reply = onsite.steps_reply("no_sign")
    assert "换3种饵" in reply


def test_mistakes_reply():
    reply = agent.handle("有什么误区", None)["reply"]
    assert "误区" in reply
    assert "饵越多越好" in reply


def test_tips_reply():
    reply = agent.handle("有哪些实操技巧", None)["reply"]
    assert "技巧" in reply
    assert "换点位" in reply


def test_beginner_reply():
    reply = agent.handle("我是新手第一次钓鱼，注意什么", None)["reply"]
    assert "安全" in reply
    assert "技巧" in reply
    assert "避坑" in reply


def test_safety_rules_reply():
    reply = agent.handle("这里禁钓吗", None)["reply"]
    assert "救生衣" in reply
    assert "泥鳅" in reply  # 全域禁止泥鳅活饵
    assert "放流" in reply


def test_llm_helpers_return_content():
    assert "救生衣" in llm.reply_for_safety_rules()
    assert "慢收停顿" in llm.reply_for_mistakes()
    assert "噪音驱鱼" in llm.reply_for_tips()


def test_tackle_advice_beginner_kit():
    reply = agent.handle("新手买什么装备", None)["reply"]
    assert "纺车轮" in reply
    assert "亮片" in reply
    assert "PE" in reply


def test_tackle_advice_by_species():
    reply = agent.handle("翘嘴用什么饵", None)["reply"]
    assert "翘嘴" in reply
    assert "亮片" in reply


def test_tackle_advice_by_rod():
    reply = agent.handle("我只有ML竿怎么配", None)["reply"]
    assert "ML" in reply
    assert "纺车轮" in reply


def test_equipment_rule_query():
    r = agent.handle("三本钩能不能用", None)
    assert "三本钩" in r["reply"]
    assert ("受限" in r["reply"]) or ("禁用" in r["reply"])


def test_spots_reply_includes_legal_reminder():
    from app.services.agent import _spots_reply
    reply = _spots_reply("杭州", [{"name": "某河", "spot_type": "回水湾", "reason": "测试", "distance_km": 1.0}])
    assert "禁渔期" in reply or "禁钓区" in reply
