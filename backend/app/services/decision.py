"""出钓决策引擎（确定性规则，可配置阈值）。

安全优先于鱼口：命中高风险时安全提示覆盖鱼口建议。
"""
from __future__ import annotations

from datetime import datetime

from ..schemas.chat import FishingContext, PlanData, PlanDetail
from .knowledge import get_species

# 安全阈值（可配置，本阶段先冻结）
_WIND_DANGER = 6  # 风力 ≥ 6 级视为大风
_HIGH_TEMP = 35  # 高温阈值（℃）

# 高风险必须直接阻断出钓
_BLOCKING_HAZARDS = {"雷暴", "暴雨", "大风", "洪水"}


def _morning_window(weather: dict) -> tuple[int, int]:
    """基于日出计算最佳低光窗口：日出到日出后 2 小时。"""
    hh, mm = (int(x) for x in weather["sunrise"].split(":"))
    return hh, (hh + 2) % 24


def _evening_window(weather: dict) -> tuple[int, int]:
    """备选窗口：日落前 2 小时到日落。"""
    hh, mm = (int(x) for x in weather["sunset"].split(":"))
    return (hh - 2) % 24, hh


def _fmt_window(start_h: int, end_h: int) -> str:
    return f"{start_h:02d}:00–{end_h:02d}:00"


def _is_night_window(window: tuple[int, int]) -> bool:
    """窗口是否跨越/落在夜间（20 点后或 5 点前）。"""
    start, end = window
    return start >= 20 or end <= 5 or start > end


def _weather_score(weather: dict, window: tuple[int, int]) -> tuple[int, list[str]]:
    """对窗口内天气打分，返回 (score, factors)。"""
    factors: list[str] = []
    start, end = window
    hours = [
        h for h in weather["hourly"]
        if start <= int(h["time"][11:13]) < end or (start > end and (int(h["time"][11:13]) >= start or int(h["time"][11:13]) < end))
    ]
    if not hours:
        hours = weather["hourly"]
    precip = max(h["precip_prob"] for h in hours)
    wind = max(h["wind_scale"] for h in hours)
    trend = hours[0]["pressure_trend"]

    score = 60
    if precip <= 20:
        score += 10
        factors.append("窗口内降水概率低")
    elif precip <= 50:
        factors.append("窗口内有短时降水可能")
    elif precip <= 70:
        score -= 15
        factors.append("降水概率较高，注意雨势")
    else:
        score -= 30
        factors.append("降水概率高，不建议出钓")

    if wind <= 3:
        score += 10
        factors.append(f"{hours[0]['wind_dir']}{wind}级，风浪适中")
    elif wind < _WIND_DANGER:
        factors.append(f"{hours[0]['wind_dir']}{wind}级，风偏大")
    else:
        score -= 20
        factors.append(f"风力达{wind}级，风险较高")

    if trend == "缓升":
        score += 10
        factors.append("气压缓升，鱼口趋好")
    elif trend == "下降":
        score -= 10
        factors.append("气压下降，活性可能降低")

    return max(0, min(score, 100)), factors


def build_plan(
    ctx: FishingContext,
    weather: dict,
    hazards: list[str],
    now: datetime | None = None,
    profile=None,
) -> PlanData:
    blocking = [h for h in hazards if h in _BLOCKING_HAZARDS]
    safety: list[str] = []
    risks: list[str] = []

    if blocking:
        safety.append(
            f"当前存在{'、'.join(blocking)}风险，安全优先：停止户外垂钓，请改期。"
        )
        return PlanData(
            location=ctx.location,
            time_window=ctx.time_label,
            target_species=ctx.target_species,
            travel_radius=ctx.travel_radius,
            conclusion="no_go",
            confidence="high",
            score=0,
            best_window=None,
            backup_window=None,
            factors=["安全风险优先于鱼口"],
            plan_detail=PlanDetail(),
            risks=[],
            safety=safety,
            data_basis=weather["meta"],
        )
    if "夜钓" in hazards:
        safety.append("夜钓风险提示：注意岸边照明、防滑与同伴同行，提前告知行程。")
    if "高温" in hazards:
        safety.append("高温提示：注意补水与中暑防护，避开正午时段。")

    species = ctx.target_species or "翘嘴"
    k = get_species(species) or get_species("翘嘴")
    assert k is not None

    mw = _morning_window(weather)
    ew = _evening_window(weather)
    score, factors = _weather_score(weather, mw)

    if score >= 75:
        conclusion = "go"
    elif score >= 50:
        conclusion = "conditional"
    else:
        conclusion = "no_go"

    confidence = "high"
    if weather["meta"].get("mock"):
        confidence = "mid"
        risks.append("天气为模拟数据，真实出钓前请以现场实测为准")
    if not ctx.target_species:
        risks.append("未指定对象鱼，已按翘嘴给出默认方案，可补充目标鱼优化")
    if ctx.location is None:
        confidence = "low"
        risks.append("位置未知，仅给标点类型建议")

    # 装备偏好联动（FR-06）：用户拟饵优先；车程限制作为默认约束
    profile_lures = (profile.lures or []) if profile else []
    profile_constraints = (profile.constraints or []) if profile else []
    if profile and profile.max_travel_radius and not ctx.travel_radius:
        ctx.travel_radius = profile.max_travel_radius
        factors.append(f"按你的车程限制 {profile.max_travel_radius}")
    if "不夜钓" in profile_constraints and _is_night_window(mw):
        safety.append("你设置了不夜钓，建议优先晨昏窗口。")

    lures = k["lures"]
    primary = lures[0]
    backup = lures[1] if len(lures) > 1 else None
    if profile_lures:
        primary = {"type": profile_lures[0], "weight": "按你的装备", "color": "常用", "action": primary["action"]}
        if len(profile_lures) > 1:
            backup = {"type": profile_lures[1], "weight": "按你的装备", "color": "常用", "action": backup["action"] if backup else primary["action"]}
        factors.append("已优先使用你的常用拟饵")
    detail = PlanDetail(
        spot_type=k["spots"][0],
        water_layer=k["water_layer"],
        primary_lure=primary["type"],
        backup_lure=backup["type"] if backup else None,
        weight_color=f"{primary['weight']}/{primary['color']}",
        action=primary["action"],
        adjust_condition="10 分钟无口则换下一水层或拟饵",
    )

    best = _fmt_window(*mw)
    backup_w = _fmt_window(*ew)
    factors.append(f"低光窗口 {best}")

    conclusion_text = {"go": "建议去", "conditional": "可去但窗口短", "no_go": "不建议"}

    return PlanData(
        location=ctx.location,
        time_window=ctx.time_label,
        target_species=species,
        travel_radius=ctx.travel_radius,
        conclusion=conclusion,
        confidence=confidence,
        score=score,
        best_window=best,
        backup_window=backup_w,
        factors=factors,
        plan_detail=detail,
        risks=risks,
        safety=safety,
        data_basis={
            "weather": weather["meta"],
            "sunrise": weather["sunrise"],
            "sunset": weather["sunset"],
            "score_breakdown": f"结论：{conclusion_text[conclusion]}",
        },
    )
