"""钓具装备解析：竿调性 → 拟饵克重范围。"""
from __future__ import annotations

import re

# 竿调性 → 舒适抛投克重范围（克）
ROD_WEIGHT_RANGE: dict[str, tuple[float, float]] = {
    "UL": (0.5, 5),
    "L": (1, 7),
    "ML": (3, 12),
    "M": (7, 21),
    "MH": (10, 28),
    "H": (15, 40),
    "XH": (20, 60),
}

# 常见竿型 → 调性（无字母调性时的兜底）
ROD_TYPE_ACTION = {
    "马口": "UL", "微物": "UL", "鳟鱼": "UL",
    "鲈鱼": "M", "翘嘴": "M", "远投": "MH",
    "雷强": "XH", "黑鱼": "H",
}


def parse_rod_action(rods: list[str]) -> str | None:
    """从竿描述中提取调性：优先匹配字母调性，其次常见竿型。"""
    if not rods:
        return None
    for rod in rods:
        if not rod:
            continue
        m = re.search(r"(XH|MH|ML|UL|H|M|L)(?![a-zA-Z])", rod.upper())
        if m:
            return m.group(1)
        for key, action in ROD_TYPE_ACTION.items():
            if key in rod:
                return action
    return None


def weight_range_for(action: str | None) -> tuple[float, float] | None:
    if not action:
        return None
    return ROD_WEIGHT_RANGE.get(action)


def parse_weight(weight_str: str) -> tuple[float, float] | None:
    """解析拟饵克重文本，如 '7–10g' → (7,10)；'微物' → None。"""
    if not weight_str:
        return None
    nums = re.findall(r"\d+(?:\.\d+)?", weight_str)
    if not nums:
        return None
    vals = [float(n) for n in nums]
    return (min(vals), max(vals))
