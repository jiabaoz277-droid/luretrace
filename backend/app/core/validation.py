"""决策后一致性校验：LLM 只负责表达，结论与约束一致性由程序保证。

存在 error 级问题时，调用方应降级为保守方案或重新计算，不得进入 LLM 自然语言生成。
"""
from __future__ import annotations

from ..schemas.chat import FishingContext, PlanData, ValidationIssue


def _window_start_hour(best_window: str | None) -> int | None:
    if not best_window:
        return None
    try:
        return int(best_window.split(":")[0])
    except Exception:  # noqa: BLE001
        return None


def validate_plan(plan: PlanData, ctx: FishingContext) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    # 目标鱼不一致
    if ctx.target_species and plan.target_species != ctx.target_species:
        issues.append(
            ValidationIssue(
                code="SPECIES_MISMATCH",
                severity="error",
                message="方案目标鱼与用户指定不一致",
            )
        )

    # 数据不完整不得高信心
    if plan.confidence == "high" and plan.data_completeness < 0.75:
        issues.append(
            ValidationIssue(
                code="OVERCONFIDENT_WITH_SPARSE_DATA",
                severity="error",
                message="数据不完整时不得输出高信心",
            )
        )

    start_h = _window_start_hour(plan.best_window)

    # 不夜钓冲突：窗口开始时间在傍晚/夜间（18 点后）
    if "不夜钓" in ctx.constraints and start_h is not None and start_h >= 18:
        issues.append(
            ValidationIssue(
                code="NIGHT_FISHING_CONFLICT",
                severity="error",
                message="方案与不夜钓约束冲突",
            )
        )

    # 推荐窗口超出用户可用时间
    if start_h is not None and (ctx.start_iso or ctx.end_iso):
        try:
            us = int(ctx.start_iso[11:13]) if ctx.start_iso and len(ctx.start_iso) >= 13 else None
            ue = int(ctx.end_iso[11:13]) if ctx.end_iso and len(ctx.end_iso) >= 13 else None
            if (us is not None and start_h < us) or (ue is not None and start_h >= ue):
                issues.append(
                    ValidationIssue(
                        code="WINDOW_OUTSIDE_USER_RANGE",
                        severity="error",
                        message="推荐窗口超出用户可用时间",
                    )
                )
        except Exception:  # noqa: BLE001
            pass

    return issues
