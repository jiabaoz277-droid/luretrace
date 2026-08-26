"""临场排障（FR-05）：确定性规则，问一个信息增益问题 → 3 步调整。

每步含观察时长与升级条件，最多 3 步，避免同时更换多个变量（PRD FR-05）。
V1.2：支持现场上下文抽取（水色/风力），明确信号不再重复追问。
"""
from __future__ import annotations

import re

from .knowledge import PRACTICAL_TIPS

# 信号 → 分类关键词（优先级从高到低）
_SIGNALS = [
    ("snag", ["挂底", "挂草", "挂障碍", "挂石头"]),
    ("lost_fish", ["跑鱼", "脱钩", "掉了", "挣脱"]),
    ("chasing", ["炸水", "追口", "追饵", "水面炸", "扑食"]),
    ("follow_not_bite", ["跟口", "不咬", "咬不中", "只跟", "蹭饵"]),
    ("no_sign", ["没口", "没鱼", "没动静", "没反应", "空军"]),
]

_STEPS: dict[str, list[dict]] = {
    "chasing": [
        {"action": "缩小拟饵规格或加快收线节奏，打炸水点附近", "duration": "10 分钟", "upgrade": "仍有炸水但打不到 → 下一步"},
        {"action": "换水面系（波爬/铅笔）沿炸水轨迹抽停", "duration": "10 分钟", "upgrade": "水面系也无追口 → 下一步"},
        {"action": "朝炸水移动方向换标点，不再原地死磕", "duration": "—", "upgrade": "—"},
    ],
    "no_sign": [
        {"action": "扩大搜索范围，换入水口/背风岸等不同标点", "duration": "15 分钟", "upgrade": "仍无口 → 下一步"},
        {"action": "换水层：中上→中下→贴底，逐层搜索", "duration": "15 分钟", "upgrade": "仍无口 → 下一步"},
        {"action": "换拟饵规格/颜色；仍无口则转场或收工", "duration": "—", "upgrade": "—"},
    ],
    "follow_not_bite": [
        {"action": "明显放慢节奏，加入停顿，让鱼咬得住", "duration": "10 分钟", "upgrade": "仍只跟不咬 → 下一步"},
        {"action": "换自然色或小一号拟饵", "duration": "10 分钟", "upgrade": "仍无改善 → 下一步"},
        {"action": "换钓组/手法（如改倒吊或换软饵），调整呈现", "duration": "—", "upgrade": "—"},
    ],
    "snag": [
        {"action": "换防挂钓组或减轻配重，贴结构边缘搜索", "duration": "10 分钟", "upgrade": "仍频繁挂底 → 下一步"},
        {"action": "换离障碍较远的标点，避开重障碍区", "duration": "10 分钟", "upgrade": "仍挂底 → 下一步"},
        {"action": "抬离底层，改为中上层搜索", "duration": "—", "upgrade": "—"},
    ],
    "lost_fish": [
        {"action": "检查钩尖是否钝，刺鱼动作更果断", "duration": "10 分钟", "upgrade": "仍跑鱼 → 下一步"},
        {"action": "换大一号钩或加强线组", "duration": "10 分钟", "upgrade": "仍跑鱼 → 下一步"},
        {"action": "放慢起鱼节奏，卸力适当放松", "duration": "—", "upgrade": "—"},
    ],
}

# 排障信号 → 对应实操技巧索引（引用 knowledge.PRACTICAL_TIPS，保持单一数据源）
_TIP_IDX = {
    "snag": 3,            # 挂底轻抖竿脱困，禁止硬拉断线丢饵
    "no_sign": 1,         # 同一钓位最多换3种饵，15–20分钟无口换点位
    "follow_not_bite": 2,  # 频繁空口：换小饵、放慢收线
    "chasing": 0,         # 抛投后等饵下沉，下落多截口
    "lost_fish": None,    # 无专属技巧，仅给通用提醒
}
_UNIVERSAL_TIP_IDX = 4  # 保持安静，噪音驱鱼


def classify_signal(text: str) -> str:
    for signal, keywords in _SIGNALS:
        if any(k in text for k in keywords):
            return signal
    return "no_sign"


# 所有信号词的扁平列表（用于判断用户是否已明确描述现场信号）
_SIGNAL_KEYWORDS = [
    "挂底", "挂草", "挂障碍", "挂石头", "跑鱼", "脱钩", "掉了", "挣脱",
    "炸水", "追口", "追饵", "水面炸", "扑食", "跟口", "不咬", "咬不中",
    "只跟", "蹭饵", "没口", "没鱼", "没动静", "没反应", "空军",
]


def has_explicit_signal(text: str) -> bool:
    """用户是否已明确描述现场信号（已描述则不再追问信号类型）。"""
    return any(k in text for k in _SIGNAL_KEYWORDS)


def extract_onsite_context(text: str) -> dict:
    """抽取现场上下文：水色 / 风力 / 无口时长。"""
    ctx: dict = {}
    if any(k in text for k in ["浑", "黄", "泥浆", "浑水", "浊"]):
        ctx["water_clarity"] = "muddy"
    elif any(k in text for k in ["清", "清澈", "透明", "清水"]):
        ctx["water_clarity"] = "clear"
    if any(k in text for k in ["大风", "风大", "狂风", "风很大", "风太大"]):
        ctx["actual_wind"] = "strong"
    elif any(k in text for k in ["无风", "没风", "风小", "微风"]):
        ctx["actual_wind"] = "calm"
    m = re.search(r"(\d{1,2}|[一二两三四五六七八九十]+)\s*(分钟|小时|钟头)", text)
    if m:
        digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                   "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        raw = m.group(1)
        n = int(raw) if raw.isdigit() else digits.get(raw)
        if n is not None:
            unit = m.group(2)
            ctx["minutes_without_bite"] = n * 60 if "小时" in unit or unit == "钟头" else n
    return ctx


def ask_diagnostic_question() -> str:
    return (
        "现在水边是什么信号？可选："
        "完全没口 / 有炸水但打不到 / 有跟口不咬 / 频繁挂底 / 跑鱼"
    )


def build_steps(signal: str) -> list[dict]:
    return _STEPS.get(signal, _STEPS["no_sign"])


def steps_reply(signal: str, context: dict | None = None) -> str:
    steps = build_steps(signal)
    context = context or {}
    lines = ["先确认现场安全：如遇大风、雷电、涨水或湿滑临水岸线，立即撤离，不要冒险。"]
    lines.append("再按顺序执行，一次只改一个变量：")

    # 现场上下文定制：风大 + 浑水
    if context.get("actual_wind") == "strong" and context.get("water_clarity") == "muddy":
        lines.append(
            "现场风大且水浑：先别硬顶风口，换到背风、站位稳的岸段；"
            "浑水里用振动更明显、对比度更高的饵攻中下层。"
        )

    for i, s in enumerate(steps, 1):
        if s["duration"] == "—":
            lines.append(f"{i}. {s['action']}；仍无改善则转场或收工。")
        else:
            line = f"{i}. {s['action']}（观察 {s['duration']}）"
            line += f"；{s['upgrade']}。" if s["upgrade"] != "—" else "。"
            lines.append(line)

    tips = []
    idx = _TIP_IDX.get(signal)
    if idx is not None and 0 <= idx < len(PRACTICAL_TIPS):
        tips.append(PRACTICAL_TIPS[idx])
    if 0 <= _UNIVERSAL_TIP_IDX < len(PRACTICAL_TIPS):
        tips.append(PRACTICAL_TIPS[_UNIVERSAL_TIP_IDX])
    if tips:
        lines.append("")
        lines.append("技巧提醒：" + "；".join(tips) + "。")
    return "\n".join(lines)
