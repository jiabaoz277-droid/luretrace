"""天气/日照查询：本阶段为 mock 数据源，统一接口预留真实接入。

真实数据接入时只需替换 get_hourly 的实现，保持返回结构不变。
"""
from __future__ import annotations

from datetime import datetime, time, timedelta


def get_hourly(location: str | None, target_date: datetime | None = None) -> dict:
    """返回逐小时天气 + 日出日落。数据为 mock，仅供链路验证。"""
    if target_date is None:
        target_date = datetime.now()
    day = target_date.date()

    # 确定性 mock：按日期微调，测试稳定
    seed = day.day % 7

    hourly = []
    for h in range(24):
        # 清晨/傍晚低光窗口风小雨少；午后降水概率升高
        if h < 9:
            precip, wind, cond = 10 + seed, 2, "多云"
        elif h < 16:
            precip, wind, cond = 55 + seed * 3, 3, "多云转阵雨"
        else:
            precip, wind, cond = 25 + seed, 2, "多云"
        pressure = 1008 + (h // 6)
        trend = "缓升" if h < 12 else "平稳"
        hourly.append(
            {
                "time": datetime.combine(day, time(h, 0)).isoformat(),
                "temp": 24 + (1 if 10 <= h <= 16 else 0),
                "precip_prob": min(precip, 90),
                "wind_scale": wind,
                "wind_dir": "东风",
                "pressure": pressure,
                "pressure_trend": trend,
                "condition": cond,
            }
        )

    return {
        "meta": {
            "location": location or "未知",
            "source": "mock",
            "mock": True,
            "updated_at": datetime.now().isoformat(timespec="minutes"),
        },
        "sunrise": "05:20",
        "sunset": "18:50",
        "hourly": hourly,
    }
