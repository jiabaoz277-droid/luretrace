"""意图识别与槽位抽取（确定性规则：正则 + 词典，离线可测）。

真实 LLM 接入后，本模块可作为降级兜底，或由 llm.extract_slots 替换解析实现。
解析器需宽容：兼容中文序号、口语时间、多种等价表达（手册第九节）。
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from ..schemas.chat import FishingContext, IntentType
from .knowledge import SPECIES_ALIASES, normalize_species

# ---------- 中文数字 ----------
_CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def _cn_to_int(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if text in _CN_NUM:
        return _CN_NUM[text]
    if text == "半":
        return None
    # 十X / X十 / X十X
    m = re.fullmatch(r"([一二两三四五六七八九])?十([一二三四五六七八九])?", text)
    if m:
        tens = _CN_NUM.get(m.group(1), 1) if m.group(1) else 1
        ones = _CN_NUM.get(m.group(2), 0) if m.group(2) else 0
        return tens * 10 + ones
    return None


# ---------- 地点 ----------
_CITIES = [
    "杭州", "上海", "北京", "南京", "苏州", "无锡", "常州", "武汉", "长沙",
    "成都", "重庆", "广州", "深圳", "天津", "西安", "合肥", "宁波", "温州",
    "嘉兴", "湖州", "绍兴", "金华", "衢州", "台州", "丽水", "舟山", "富阳",
    "桐庐", "建德", "淳安", "临安", "余杭", "萧山", "滨江", "西湖",
]
_WATERS = [
    "富春江", "钱塘江", "千岛湖", "西湖", "湘湖", "太湖", "南湖", "京杭大运河",
    "新安江", "分水江", "苕溪", "瓯江",
]


def _extract_location(text: str) -> str | None:
    # 从X出发 / X周边 / X附近 / X周边X小时
    m = re.search(r"从([\u4e00-\u9fa5A-Za-z0-9]{2,12})出发", text)
    if m:
        return m.group(1)
    for w in _WATERS:
        if w in text:
            return w
    for c in _CITIES:
        if c in text:
            return c
    m = re.search(r"([\u4e00-\u9fa5]{2,6})(?:周边|附近|一带)", text)
    if m:
        return m.group(1)
    return None


# ---------- 时间 ----------
_DATE_KEYS: dict[str, int] = {
    "今天": 0, "今日": 0, "今早": 0, "今晚": 0,
    "明天": 1, "明日": 1, "明早": 1, "明晨": 1, "明晚": 1,
    "后天": 2, "后日": 2, "后天早": 2,
}
_WEEKDAY_CN = {
    "周一": 0, "星期一": 0, "周二": 1, "星期二": 1, "周三": 2, "星期三": 2,
    "周四": 3, "星期四": 3, "周五": 4, "星期五": 4, "周六": 5, "星期六": 5,
    "周日": 6, "周天": 6, "星期日": 6, "星期天": 6, "礼拜六": 5, "礼拜天": 6,
}

# 时段默认窗口（小时）
_TIME_SLOT = {
    "凌晨": (0, 5), "清晨": (5, 7), "早上": (5, 9), "早晨": (5, 9),
    "上午": (8, 11), "中午": (11, 13), "下午": (13, 18), "傍晚": (17, 19),
    "晚上": (18, 22), "夜间": (20, 23), "夜里": (20, 23),
    "下班后": (18, 22), "半夜": (20, 23), "一早": (5, 9), "大清早": (5, 9), "午后": (13, 18),
}


def _parse_time(text: str, now: datetime) -> dict | None:
    """解析时间，返回 {label, start_iso, end_iso}；无法解析返回 None。"""
    target_date = now.date()
    date_key = None
    for k, offset in _DATE_KEYS.items():
        if k in text:
            date_key = k
            target_date = now.date() + timedelta(days=offset)
            break
    if date_key is None:
        for k, wd in _WEEKDAY_CN.items():
            if k in text:
                target_date = now.date() + timedelta(days=(wd - now.weekday()) % 7)
                date_key = k
                break
    # "周末" → 下一个周六
    if date_key is None and "周末" in text:
        days = (5 - now.weekday()) % 7
        if days == 0:
            days = 7
        target_date = now.date() + timedelta(days=days)
        date_key = "周末"

    # 显式小时范围：5-9点 / 5点到9点 / 5:00-9:00
    start_hour = end_hour = None
    m = re.search(r"(\d{1,2}|[一二两三四五六七八九十]+)\s*[:：点]?\s*[-到至~]\s*(\d{1,2}|[一二两三四五六七八九十]+)\s*点?", text)
    if m:
        a, b = _cn_to_int(m.group(1)), _cn_to_int(m.group(2))
        if a is not None and b is not None and 0 <= a <= 24 and 0 <= b <= 24:
            start_hour, end_hour = a, b
    if start_hour is None:
        # 时段关键词
        for k, (a, b) in _TIME_SLOT.items():
            if k in text:
                start_hour, end_hour = a, b
                break
    if start_hour is None:
        # 只有日期没有时段 → 按“早/晚/晨”推断默认窗口，否则默认清晨（路亚最常见）
        if date_key is not None:
            if "晚" in date_key or "夜" in date_key:
                start_hour, end_hour = 18, 22
            else:
                start_hour, end_hour = 5, 9
    if start_hour is None:
        return None

    start_hour = max(0, min(start_hour, 23))
    end_hour = max(0, min(end_hour, 23))

    start_dt = datetime.combine(target_date, time(start_hour, 0))
    end_dt = datetime.combine(target_date, time(end_hour, 0))
    date_str = f"{target_date.month}月{target_date.day}日"
    label = f"{date_str} {start_hour:02d}:00–{end_hour:02d}:00"
    return {
        "label": label,
        "start_iso": start_dt.isoformat(),
        "end_iso": end_dt.isoformat(),
        "resolved": True,
    }


# ---------- 出行半径 ----------
def _extract_radius(text: str) -> str | None:
    m = re.search(r"(\d{1,3}|[一二两三四五六七八九十]+)\s*(公里|千米|km|KM)", text)
    if m:
        n = _cn_to_int(m.group(1))
        if n is not None:
            return f"{n}公里"
    m = re.search(r"(半|[一二两三四五六七八九十]+|\d{1,2})\s*(个?小时|分钟|钟头|h|H)", text)
    if m:
        if m.group(1) == "半":
            return "30分钟"
        n = _cn_to_int(m.group(1))
        if n is not None:
            unit = m.group(2)
            return f"{n}小时" if "小时" in unit else f"{n}分钟"
    return None


# ---------- 水域类型 ----------
def _extract_water_type(text: str) -> str | None:
    for w in ["江河", "水库", "湖泊", "溪流", "江", "河", "湖", "库", "溪"]:
        if w in text:
            return w
    return None


# ---------- 约束 ----------
_CONSTRAINTS = {
    "不夜钓": "不夜钓", "不涉水": "不涉水", "带孩子": "带孩子",
    "不开车": "不开车", "不坐船": "不坐船", "不跑太远": "不跑太远",
    "只带微物竿": "只带微物竿", "一个人": "一个人",
}


def _extract_constraints(text: str) -> list[str]:
    found = []
    for k, v in _CONSTRAINTS.items():
        if k in text:
            found.append(v)
    return found


# ---------- 装备 ----------
_TACKLE_HINTS = [
    "ML竿", "M竿", "MH竿", "L竿", "UL竿", "微物竿", "马口竿", "枪柄", "直柄",
    "亮片", "米诺", "铅笔", "波爬", "雷蛙", "VIB", "软饵", "德州", "倒吊",
]


def _extract_tackle(text: str) -> str | None:
    hits = [t for t in _TACKLE_HINTS if t.lower() in text.lower()]
    return "、".join(hits) if hits else None


def detect_intent(text: str) -> IntentType:
    # 复盘信号优先于“空军/没口”等临场信号
    if any(k in text for k in ["复盘", "战报", "记一下", "上鱼了", "今天钓了"]):
        return "CATCH_REVIEW"
    if any(k in text for k in ["没口", "没鱼", "不咬", "空军", "打不到", "挂底", "跑鱼"]):
        return "ON_SITE_TROUBLESHOOT"
    if any(k in text for k in ["禁钓", "能不能钓", "违规", "雷暴", "安全吗", "危险"]):
        return "SAFETY_OR_RULES"
    if any(k in text for k in ["是什么", "为什么", "习性", "介绍", "什么是", "怎么区分", "怎么钓", "怎么路亚", "如何钓", "能路亚吗", "能不能路亚", "可以路亚吗", "适合路亚吗", "好路亚吗"]):
        return "KNOWLEDGE_QA"
    if any(k in text for k in ["什么饵", "怎么配", "用什么", "装备", "竿", "怎么打", "拟饵", "搭配"]):
        return "TACKLE_ADVICE"
    if any(k in text for k in ["几点", "什么时候", "什么时段", "时段", "哪个时间"]):
        return "CHOOSE_TIME"
    if any(k in text for k in ["去哪", "哪里", "哪个地方", "什么地方", "哪个点", "什么点"]):
        return "CHOOSE_PLACE"
    if any(k in text for k in ["值得去", "能去吗", "可以去吗", "适不适合", "要不要去", "能钓吗", "行不行"]):
        return "GO_OR_NOT"
    if any(k in text for k in ["去", "路亚", "钓鱼", "出钓", "打", "甩两竿", "钓", "搞"]):
        return "PLAN_TRIP"
    return "UNKNOWN"


def detect_hazards(text: str) -> list[str]:
    """从输入中识别高风险关键词，用于安全规则命中（确定性阈值，不依赖模型自觉）。"""
    found = []
    for kw, label in [
        ("雷暴", "雷暴"), ("雷电", "雷暴"), ("打雷", "雷暴"),
        ("暴雨", "暴雨"), ("大风", "大风"), ("台风", "大风"),
        ("洪水", "洪水"), ("涨水", "洪水"), ("高温", "高温"),
        ("夜钓", "夜钓"), ("夜里去", "夜钓"), ("晚上去", "夜钓"),
    ]:
        if kw in text and label not in found:
            found.append(label)
    return found


def extract_slots(text: str, now: datetime) -> FishingContext:
    """从一句话中抽取槽位（只返回本句新发现的内容）。"""
    ctx = FishingContext()
    ctx.location = _extract_location(text)
    t = _parse_time(text, now)
    if t:
        ctx.time_window = text
        ctx.time_label = t["label"]
        ctx.start_iso = t["start_iso"]
        ctx.end_iso = t["end_iso"]
    for alias, species in SPECIES_ALIASES.items():
        if alias in text:
            ctx.target_species = species
            break
    ctx.travel_radius = _extract_radius(text)
    ctx.water_type = _extract_water_type(text)
    ctx.constraints = _extract_constraints(text)
    ctx.tackle = _extract_tackle(text)
    return ctx


def missing_slots(ctx: FishingContext) -> list[str]:
    """返回需要追问的槽位（按 PRD 9.1 优先级：地点 > 目标鱼）。

    出行半径/装备/水域类型为可选槽位：提供了就用于优化，未提供不阻断生成。
    """
    missing = []
    if not ctx.location:
        missing.append("location")
    if not ctx.target_species:
        missing.append("target_species")
    return missing
