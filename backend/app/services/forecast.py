"""多日出钓预报：逐日打分排序，推荐最佳出钓日与窗口。"""
from __future__ import annotations

from datetime import datetime

from .knowledge import season_strategy
from .weather import get_daily_forecast

# 高风险天气直接否决
_BLOCKING_COND = ("雷", "暴雨", "暴雪", "台风")


def _score_day(day: dict) -> tuple[int, list[str]]:
    """对单日天气打分，返回 (score, factors)。"""
    factors: list[str] = []
    score = 60

    # 天气现象（雷暴/暴雨直接否决）
    cond = day.get("condition", "")
    if any(k in cond for k in _BLOCKING_COND):
        score -= 40
        factors.append(cond)

    # 降水概率
    p = day.get("precip_prob", 0)
    if p <= 20:
        score += 10
        factors.append("降水概率低")
    elif p <= 50:
        factors.append("可能有短时降水")
    else:
        score -= 20
        factors.append("降水概率较高")

    # 风力
    w = day.get("wind_scale", 0)
    if w <= 3:
        score += 10
        factors.append(f"{day.get('wind_dir', '')}{w}级")
    elif w < 6:
        factors.append(f"风偏大({w}级)")
    else:
        score -= 20
        factors.append("大风")

    # 气温极端
    if day.get("temp_max", 30) >= 35:
        score -= 10
        factors.append("高温")
    if day.get("temp_min", 10) <= 5:
        score -= 15
        factors.append("低温，鱼口差")

    return max(0, min(score, 100)), factors


def build_forecast(location: str | None, days: int = 7) -> dict:
    """未来 N 天逐日打分，返回按评分降序的结果与季节提示。"""
    daily = get_daily_forecast(location, days)
    season_tip = ""
    try:
        s = season_strategy(datetime.now().month)
        if s:
            season_tip = f"{s['name']}季：{s['strategy']}"
    except Exception:  # noqa: BLE001
        pass

    results = []
    for d in daily:
        score, factors = _score_day(d)
        results.append(
            {
                "date": d.get("date", ""),
                "score": score,
                "condition": d.get("condition", ""),
                "temp": f"{d.get('temp_min', 0):.0f}–{d.get('temp_max', 0):.0f}℃",
                "wind": f"{d.get('wind_dir', '')}{d.get('wind_scale', 0)}级",
                "best_window": f"{d.get('sunrise', '06:00')} 前后 / {d.get('sunset', '18:00')} 前后",
                "factors": factors,
            }
        )
    results.sort(key=lambda x: (-x["score"], x["date"]))
    warning = next((d.get("warning") for d in daily if d.get("warning")), None)
    return {
        "results": results,
        "season_tip": season_tip,
        "source": location,
        "data_status": "degraded" if any(d.get("mock") for d in daily) else "live",
        "warning": warning,
    }


def forecast_reply(location: str | None, days: int = 7) -> str:
    """把预报结果整理成老付式回复。"""
    data = build_forecast(location, days)
    results = data["results"]
    if not results:
        return "这几天的预报老付暂时查不到，稍后再试。"
    label = location or "你这里"
    lines = [f"老付看了下 {label} 未来几天，按出钓划算程度排个序："]
    for i, r in enumerate(results[:3], 1):
        star = "★" if i == 1 else "☆"
        lines.append(
            f"{i}. {_fmt_date(r['date'])} {star} 评分 {r['score']}｜{r['condition']}，{r['temp']}，{r['wind']}"
            f"\n   最佳窗口：{r['best_window']}"
        )
    if data["season_tip"]:
        lines.append(data["season_tip"])
    if data.get("warning"):
        lines.append(f"数据提示：{data['warning']}。")
    lines.append("评分只是出钓参考，不保证上鱼；雷暴、大风天别去。")
    lines.append("出发前查一下当地禁渔期和禁钓区，合规垂钓。")
    return "\n".join(lines)


def _fmt_date(iso: str) -> str:
    """'2026-08-25' → '8月25日'。"""
    parts = iso.split("-")
    if len(parts) == 3:
        return f"{int(parts[1])}月{int(parts[2])}日"
    return iso
