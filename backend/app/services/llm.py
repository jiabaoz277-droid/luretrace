"""模型抽象层：开发期用模板 mock，真实 Key 接入后替换为 LLM 调用。

真实 LLM 接入点：将 reply_* 函数改为调用 chat 模型，并用 Pydantic 校验结构化输出。
"""
from __future__ import annotations

from ..schemas.chat import PlanData


def reply_for_clarify(missing: str) -> str:
    if missing == "location":
        return "你从哪里出发？可以直接说城市或水域，也可以授权当前位置。"
    if missing == "target_species":
        return "想打什么目标鱼？比如：翘嘴、鳜鱼、鲈鱼（直接回复鱼名即可）。"
    return "还缺一点信息，请补充后再给你方案。"


def reply_for_plan(plan: PlanData) -> str:
    conclusion_text = {"go": "建议去", "conditional": "可去但窗口短", "no_go": "不建议"}
    lines = []
    if plan.conclusion == "no_go" and plan.safety:
        lines.append("⚠️ " + plan.safety[0])
        return "\n".join(lines)

    head = conclusion_text[plan.conclusion]
    if plan.conclusion == "conditional":
        head += f"，只抓 {plan.best_window or '关键窗口'}"
    head += f"（信心{'高' if plan.confidence=='high' else '中' if plan.confidence=='mid' else '低'}）"
    lines.append(head)

    if plan.best_window:
        lines.append(f"最佳窗口：{plan.best_window}" + (f"；备选：{plan.backup_window}" if plan.backup_window else ""))

    d = plan.plan_detail
    parts = [p for p in [d.spot_type, d.water_layer, d.primary_lure, d.weight_color, d.action] if p]
    if parts:
        lines.append("方案：" + "，".join(parts) + "。")

    if plan.factors:
        lines.append("依据：" + "；".join(plan.factors[:3]) + "。")

    if plan.risks:
        lines.append("注意：" + "；".join(plan.risks[:2]) + "。")
    if plan.safety:
        lines.append("安全：" + "；".join(plan.safety) + "。")
    lines.append("下一步：可告诉我“改成下午/换目标鱼/改距离”，我会只重算受影响部分。")
    return "\n".join(lines)


def reply_for_knowledge(species: str) -> str:
    from .knowledge import get_species

    k = get_species(species)
    if not k:
        return "我还不太了解这种鱼，可以试试问翘嘴、鳜鱼、鲈鱼等常见淡水路亚对象鱼。"
    lures = "、".join(f"{l['type']}({l['weight']})" for l in k["lures"][:2])
    return (
        f"{species}：目标水层以{k['water_layer']}为主，活跃时段多在{k['prime_time']}，"
        f"常见标点有{'、'.join(k['spots'][:2])}。常用拟饵：{lures}。"
    )


def reply_out_of_scope(intent: str) -> str:
    if intent == "ON_SITE_TROUBLESHOOT":
        return "临场排障将在后续阶段开放。本阶段可先帮你规划出钓方案，告诉我时间、地点和目标鱼即可。"
    if intent == "CATCH_REVIEW":
        return "战报复盘将在后续阶段开放。本阶段可先帮你规划出钓方案。"
    return "这个问题暂未覆盖，你可以先问我“今天值得去吗”“去哪打翘嘴”等出钓决策问题。"
