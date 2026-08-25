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
    assert detect_intent("明早想去路亚") == "PLAN_TRIP"
    assert detect_intent("今天值得去吗") == "GO_OR_NOT"
    assert detect_intent("今天几点打翘嘴最好") == "CHOOSE_TIME"
    assert detect_intent("一小时车程内去哪") == "CHOOSE_PLACE"
    assert detect_intent("我只有ML竿和7g亮片怎么打") == "TACKLE_ADVICE"
    assert detect_intent("到了半小时没口怎么办") == "ON_SITE_TROUBLESHOOT"
    assert detect_intent("空军了帮我复盘") == "CATCH_REVIEW"
    assert detect_intent("翘嘴什么习性") == "KNOWLEDGE_QA"
    assert detect_intent("雷暴天能去吗") == "SAFETY_OR_RULES"


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

    assert missing_slots(FishingContext()) == ["location", "target_species"]
    assert missing_slots(FishingContext(location="杭州")) == ["target_species"]
    assert missing_slots(FishingContext(location="杭州", target_species="翘嘴")) == []


def test_detect_hazards():
    assert "雷暴" in detect_hazards("雷暴天能去吗")
    assert "夜钓" in detect_hazards("今晚夜钓行不行")
    assert detect_hazards("明早去钓鱼") == []
