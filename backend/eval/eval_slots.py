"""槽位抽取验收评测（FR-01）。

用法（在 backend/ 目录下）：
    .venv/bin/python -m eval.eval_slots              # 规则 + LLM（配置了 Key 时）
    .venv/bin/python -m eval.eval_slots --offline    # 仅规则，离线
"""
from __future__ import annotations

import argparse
from datetime import datetime

from app.services import llm
from app.services.agent import extract_merged_slots
from eval.corpus import HARD_CASES, STANDARD_CASES

NOW = datetime(2026, 8, 25, 10, 0)  # 固定"现在"，保证相对时间可断言


def _loc_match(got: str | None, expect: str | None) -> bool:
    """地点匹配：相等，或非空时互相包含（如“杭州西湖” vs “西湖”同指一处）。"""
    if got == expect:
        return True
    if got and expect and (expect in got or got in expect):
        return True
    return False


def run(cases: list[dict], now: datetime) -> tuple[dict, list[dict]]:
    stats = {"location": 0, "species": 0, "time": 0, "all": 0, "total": len(cases)}
    failures: list[dict] = []
    for c in cases:
        ctx = extract_merged_slots(c["text"], now)
        loc_ok = _loc_match(ctx.location, c["location"])
        sp_ok = ctx.target_species == c["species"]
        time_ok = (ctx.time_label is not None) if c["time_resolved"] else (ctx.time_label is None)

        if loc_ok:
            stats["location"] += 1
        if sp_ok:
            stats["species"] += 1
        if time_ok:
            stats["time"] += 1
        if loc_ok and sp_ok and time_ok:
            stats["all"] += 1
        else:
            failures.append(
                {
                    "text": c["text"],
                    "expect": (c["location"], c["species"], c["time_resolved"]),
                    "got": (ctx.location, ctx.target_species, ctx.time_label),
                }
            )
    return stats, failures


def _pct(n: int, total: int) -> str:
    return f"{n}/{total} = {n / total * 100:.1f}%"


def report(name: str, stats: dict, failures: list[dict]) -> None:
    n = stats["total"]
    print(f"\n=== {name} ===")
    print(f"location 准确率 : {_pct(stats['location'], n)}")
    print(f"species  准确率 : {_pct(stats['species'], n)}")
    print(f"time 解析正确率 : {_pct(stats['time'], n)}")
    print(f"三槽位完全正确 : {_pct(stats['all'], n)}")
    if failures:
        print(f"失败 {len(failures)} 条：")
        for f in failures[:30]:
            exp_time = "有时间" if f["expect"][2] else "无时间"
            print(f"  「{f['text']}」 期望=({f['expect'][0]},{f['expect'][1]},{exp_time}) 实际=({f['got'][0]},{f['got'][1]},{f['got'][2]})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只测规则，不调 LLM")
    args = ap.parse_args()

    if args.offline:
        llm.is_configured = lambda: False
        mode = "离线规则（不含 LLM）"
    elif llm.is_configured():
        mode = "规则 + LLM 增强"
    else:
        mode = "规则（未配置 Key）"
    print(f"评测模式：{mode}")

    for name, cases in [
        ("标准语料（50 条，FR-01 目标 ≥90%）", STANDARD_CASES),
        ("边界/难例（50 条）", HARD_CASES),
    ]:
        stats, failures = run(cases, NOW)
        report(name, stats, failures)

    std_stats, _ = run(STANDARD_CASES, NOW)
    print(f"\n[FR-01 达标判断] 标准语料三槽位完全正确率 {_pct(std_stats['all'], std_stats['total'])}，目标 ≥90%")


if __name__ == "__main__":
    main()
