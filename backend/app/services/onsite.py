"""临场排障（FR-05）：确定性规则，问一个信息增益问题 → 3 步调整。

每步含观察时长与升级条件，最多 3 步，避免同时更换多个变量（PRD FR-05）。
"""
from __future__ import annotations

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


def classify_signal(text: str) -> str:
    for signal, keywords in _SIGNALS:
        if any(k in text for k in keywords):
            return signal
    return "no_sign"


def ask_diagnostic_question() -> str:
    return (
        "现在水边是什么信号？可选："
        "完全没口 / 有炸水但打不到 / 有跟口不咬 / 频繁挂底 / 跑鱼"
    )


def build_steps(signal: str) -> list[dict]:
    return _STEPS.get(signal, _STEPS["no_sign"])


def steps_reply(signal: str) -> str:
    steps = build_steps(signal)
    lines = ["按顺序执行，一次只改一个变量："]
    for i, s in enumerate(steps, 1):
        line = f"{i}. {s['action']}（观察 {s['duration']}）"
        if s["upgrade"] != "—":
            line += f"；{s['upgrade']}。"
        else:
            line += "。"
        lines.append(line)
    return "\n".join(lines)
