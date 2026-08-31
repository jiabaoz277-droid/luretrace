"""意图识别与槽位抽取测试（确定性规则，离线可跑）。"""
from datetime import datetime

from app.services.intent import (
    detect_hazards,
    detect_intent,
    extract_slots,
    missing_slots,
)

NOW = datetime(2026, 8, 25, 10, 0)  # 固定"现在"，保证相对时间可断言


def test_detect_intent():
    assert detect_intent("明早想去路亚").primary_intent == "PLAN_TRIP"
    r = detect_intent("今天值得去吗")
    assert r.primary_intent == "PLAN_TRIP" and "GO_OR_NOT" in r.secondary_intents
    r = detect_intent("今天几点打翘嘴最好")
    assert r.primary_intent == "PLAN_TRIP" and "CHOOSE_TIME" in r.secondary_intents
    r = detect_intent("一小时车程内去哪")
    assert r.primary_intent == "PLAN_TRIP" and "CHOOSE_PLACE" in r.secondary_intents
    assert detect_intent("我只有ML竿和7g亮片怎么打").primary_intent == "TACKLE_QA"
    assert detect_intent("到了半小时没口怎么办").primary_intent == "ON_SITE_TROUBLESHOOT"
    assert detect_intent("空军了帮我复盘").primary_intent == "CATCH_REPORT"
    assert detect_intent("翘嘴什么习性").primary_intent == "KNOWLEDGE_QA"
    assert detect_intent("鲈鱼的钓法").primary_intent == "KNOWLEDGE_QA"
    assert detect_intent("我是新手不会钓").primary_intent == "KNOWLEDGE_QA"
    assert detect_intent("路亚小白，没钓过").primary_intent == "KNOWLEDGE_QA"
    assert detect_intent("雷暴天能去吗").primary_intent == "SAFETY_STOP"


def test_plan_intent_wins_over_tackle_terms():
    """含装备的完整出钓需求不得被误分类为装备问答（任务书 2.1 回归用例）。"""
    text = "明早杭州周边两小时打翘嘴，不夜钓，只有ML竿和7g亮片"
    result = detect_intent(text)
    assert result.primary_intent == "PLAN_TRIP"
    assert "TACKLE_QA" in result.secondary_intents


def test_plan_context_wins_over_knowledge_wording():
    """带时间和对象鱼的“钓法”是出钓任务，不应被新知识词反向误伤。"""
    result = detect_intent("明天去杭州钓鲈鱼，给个钓法")
    assert result.primary_intent == "PLAN_TRIP"


def test_explicit_trip_context_wins_over_beginner_wording():
    result = detect_intent("明早杭州，我是新手不会钓")
    assert result.primary_intent == "PLAN_TRIP"


def test_extract_slots_full():
    ctx = extract_slots("明早杭州周边两小时，想打翘嘴", NOW)
    assert ctx.location == "杭州"
    assert ctx.target_species == "翘嘴"
    assert ctx.travel_radius == "2小时"
    assert ctx.time_label is not None
    assert ctx.time_label.startswith("8月26日")  # 明早 = 明天


def test_extract_relative_time():
    ctx = extract_slots("明早5点到9点", NOW)
    assert ctx.start_iso.startswith("2026-08-26T05:00")
    assert ctx.end_iso.startswith("2026-08-26T09:00")


def test_today_plain_uses_rest_of_day():
    """纯“今天”无时段 → 窗口从当前时刻到晚间，不把已过去的清晨当建议。"""
    now = datetime(2026, 8, 25, 11, 0)
    ctx = extract_slots("今天可以钓吗", now)
    assert ctx.start_iso.startswith("2026-08-25T11:00")
    assert ctx.end_iso.startswith("2026-08-25T22:00")


def test_today_early_morning_window_still_available():
    """凌晨问“今天”时，清晨窗口仍未过去，窗口从当前时刻起。"""
    now = datetime(2026, 8, 25, 4, 0)
    ctx = extract_slots("今天可以钓吗", now)
    assert ctx.start_iso.startswith("2026-08-25T04:00")
    assert ctx.end_iso.startswith("2026-08-25T22:00")


def test_extract_weekend():
    ctx = extract_slots("周末想去钓鱼", NOW)
    # 2026-08-25 是周二；下一个周六是 8-29
    assert ctx.start_iso.startswith("2026-08-29")


def test_extract_tackle_and_constraint():
    ctx = extract_slots("我只有ML竿和7g亮片，不夜钓", NOW)
    assert "ML竿" in (ctx.tackle or "")
    assert "亮片" in (ctx.tackle or "")
    assert "不夜钓" in ctx.constraints


def test_missing_slots_priority():
    from app.schemas.chat import FishingContext

    assert missing_slots(FishingContext()) == ["location"]
    assert missing_slots(FishingContext(location="杭州")) == []
    assert missing_slots(FishingContext(location="杭州", target_species="翘嘴")) == []


def test_detect_hazards():
    assert "雷暴" in detect_hazards("雷暴天能去吗")
    assert "夜钓" in detect_hazards("今晚夜钓行不行")
    assert detect_hazards("明早去钓鱼") == []
