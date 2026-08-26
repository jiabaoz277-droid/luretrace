"""出钓决策引擎（确定性规则，可配置阈值）。

安全优先于鱼口：命中高风险时安全提示覆盖鱼口建议。
"""
from __future__ import annotations

from datetime import datetime

from ..schemas.chat import FishingContext, PlanData, PlanDetail
from . import tackle
from .knowledge import (
    PRESSURE_OPTIMAL,
    PRESSURE_STOP,
    WATER_TEMP_STOP,
    get_species,
    season_strategy,
)

# 安全阈值（可配置，本阶段先冻结）
_WIND_DANGER = 6  # 风力 ≥ 6 级视为大风
_HIGH_TEMP = 35  # 高温阈值（℃）

# 高风险必须直接阻断出钓
_BLOCKING_HAZARDS = {"雷暴", "暴雨", "大风", "洪水"}

# 冬季作钓偏好（SEASON_STRATEGY）
_WINTER_WINDOW = (10, 14)  # 正午窗口：10:00–14:00
_WINTER_LURE_KEYWORDS = ("软饵", "VIB", "铁板", "德州", "铅头钩", "卡罗", "倒吊", "虫")


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


def _pressure_factor(hours: list[dict]) -> tuple[int, str | None]:
    """气压绝对值评分（ENV_RULES 阈值：1005–1025 最佳，<990 停口）。"""
    pressures = [h.get("pressure", 0) for h in hours if h.get("pressure")]
    if not pressures:
        return 0, None
    avg = sum(pressures) / len(pressures)
    low = min(pressures)
    if low < PRESSURE_STOP:
        return -30, f"气压低至 {low:.0f} hPa（<{PRESSURE_STOP}），鱼口可能停滞"
    if PRESSURE_OPTIMAL[0] <= avg <= PRESSURE_OPTIMAL[1]:
        return 10, f"气压 {avg:.0f} hPa 处于最佳区间"
    return -5, f"气压 {avg:.0f} hPa，偏离最佳区间"


def _temp_factor(hours: list[dict]) -> tuple[int, str | None]:
    """气温（水温代理）评分（ENV_RULES 阈值：<10℃ 活性暴跌）。"""
    temps = [h.get("temp", 0) for h in hours if h.get("temp")]
    if not temps:
        return 0, None
    low = min(temps)
    if low < WATER_TEMP_STOP:
        return -20, f"气温低至 {low:.0f}℃，水温可能偏低、掠食鱼活性下降"
    return 0, None


def _winter_lure(lures: list[dict]) -> dict | None:
    """冬季优先软饵/VIB/铁板等慢收拟饵。"""
    for lure in lures:
        if any(k in lure["type"] for k in _WINTER_LURE_KEYWORDS):
            return lure
    return None


def hourly_fish_scores(hourly: list[dict]) -> list[dict]:
    """逐小时鱼口参考分（0-100），供首页看板展示。"""
    result = []
    for h in hourly:
        score = 60
        p = h.get("precip_prob", 0) or 0
        if p <= 20:
            score += 10
        elif p > 70:
            score -= 30
        elif p > 50:
            score -= 15

        w = h.get("wind_scale", 0) or 0
        if w <= 3:
            score += 10
        elif w >= 6:
            score -= 20

        press = h.get("pressure", 0) or 0
        if press and press < 990:
            score -= 30
        elif press and 1005 <= press <= 1025:
            score += 10

        t = h.get("temp", 20) or 20
        if t < 10:
            score -= 20
        elif t >= 35:
            score -= 10

        trend = h.get("pressure_trend")
        if trend == "缓升":
            score += 10
        elif trend == "下降":
            score -= 10

        score = max(0, min(score, 100))
        time_str = h.get("time", "")
        hour_str = time_str[11:13] if len(time_str) >= 13 else "?"
        result.append(
            {
                "hour": hour_str,
                "score": score,
                "temp": round(h.get("temp", 0) or 0),
                "condition": h.get("condition", ""),
            }
        )
    return result


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

    # 气压绝对值 + 气温（水温代理）—— ENV_RULES 硬阈值
    p_score, p_factor = _pressure_factor(hours)
    score += p_score
    if p_factor:
        factors.append(p_factor)
    t_score, t_factor = _temp_factor(hours)
    score += t_score
    if t_factor:
        factors.append(t_factor)

    return max(0, min(score, 100)), factors


def build_plan(
    ctx: FishingContext,
    weather: dict,
    hazards: list[str],
    now: datetime | None = None,
    profile=None,
) -> PlanData:
    now = now or datetime.now()
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

    season = season_strategy(now.month)
    mw = _morning_window(weather)
    ew = _evening_window(weather)
    is_winter = bool(season and season["name"] == "冬")
    if is_winter:
        mw = _WINTER_WINDOW
    score, factors = _weather_score(weather, mw)
    if season:
        factors.append(f"{season['name']}季：{season['strategy']}")

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
    avoid_methods = (profile.avoid_methods or []) if profile else []
    if profile and profile.max_travel_radius and not ctx.travel_radius:
        ctx.travel_radius = profile.max_travel_radius
        factors.append(f"按你的车程限制 {profile.max_travel_radius}")
    if "不夜钓" in profile_constraints and _is_night_window(mw):
        safety.append("你设置了不夜钓，建议优先晨昏窗口。")
    if avoid_methods:
        risks.append(f"你标记了不愿用：{'、'.join(avoid_methods)}，方案如有涉及请自行调整")

    # 竿调性 → 拟饵克重建议（FR-06）
    rod_action = None
    rod_range = None
    if profile and profile.rods:
        rod_action = tackle.parse_rod_action(profile.rods)
        rod_range = tackle.weight_range_for(rod_action)

    lures = k["lures"]
    primary = lures[0]
    backup = lures[1] if len(lures) > 1 else None

    if rod_action and rod_range:
        factors.append(f"你的 {rod_action} 竿适合 {rod_range[0]:g}–{rod_range[1]:g}g 拟饵")
        rec = tackle.parse_weight(primary["weight"])
        if rec and (rec[1] < rod_range[0] or rec[0] > rod_range[1]):
            risks.append(f"该鱼推荐 {primary['weight']}，可能超出你 {rod_action} 竿的舒适范围")
    if profile_lures:
        primary = {"type": profile_lures[0], "weight": "按你的装备", "color": "常用", "action": primary["action"]}
        backup = lures[0]  # 备选保留鱼种推荐拟饵，避免用户装备不适配目标鱼时无解
        factors.append("已优先使用你的常用拟饵")
        risks.append("若 10 分钟无口，可换该鱼推荐拟饵再试")

    # 冬季策略：优先软饵/VIB，慢收长停顿
    action = primary["action"]
    if is_winter:
        winter_lure = _winter_lure(lures)
        if winter_lure and not profile_lures and winter_lure is not primary:
            backup = primary
            primary = winter_lure
        action = "慢收长停顿"

    detail = PlanDetail(
        spot_type=k["spots"][0],
        water_layer=k["water_layer"],
        primary_lure=primary["type"],
        backup_lure=backup["type"] if backup else None,
        weight_color=f"{primary['weight']}/{primary['color']}",
        action=action,
        adjust_condition=("15–20 分钟无口则换点或收工" if is_winter else "10 分钟无口则换下一水层或拟饵"),
    )

    best = _fmt_window(*mw)
    backup_w = _fmt_window(*ew) if not is_winter else None
    if is_winter:
        factors.append(f"正午窗口 {best}")
    else:
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
