"""模型抽象层：真实 LLM（OpenAI 兼容接口）优先，规则/模板兜底。

- 已配置 Key：槽位抽取 + 自然语言回复走真实模型；决策引擎仍为确定性规则。
- 未配置 Key 或调用失败：自动回退到确定性规则解析 + 模板回复，不影响核心链路。
- 安全提示永远由确定性代码保证，不交给模型决定（安全优先于鱼口）。
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime

import httpx

from ..core.config import settings
from ..schemas.chat import FishingContext, PlanData
from . import intent as intent_rules
from . import tackle
from . import prompts
from .knowledge import (
    BEGINNER_KIT,
    LINE_GUIDE,
    LINE_PAIRING,
    LURE_SELECTION_RULE,
    REEL_GUIDE,
    ROD_TARGET,
    SPECIES_ALIASES,
    get_species,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
_TIMEOUT = 30.0
_MAX_RETRIES = 2

# 合规提醒（P0）：所有确定性知识/装备回复末尾统一追加
def _compliance_note() -> str:
    return prompts.get_text("compliance_note")


def is_configured() -> bool:
    return bool(settings.model_api_key)


def _base_url() -> str:
    return (settings.model_base_url or DEFAULT_BASE_URL).rstrip("/")


def _model() -> str:
    return settings.model_name or DEFAULT_MODEL


def chat_completion(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 800,
    json_mode: bool = False,
) -> str:
    """调用 OpenAI 兼容接口，带有限重试；不把密钥或响应体中的敏感信息透出。"""
    if not is_configured():
        raise RuntimeError("未配置模型 API Key")
    url = f"{_base_url()}/chat/completions"
    payload: dict = {
        "model": _model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {
        "Authorization": f"Bearer {settings.model_api_key}",
        "Content-Type": "application/json",
    }

    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 401:
                raise RuntimeError("API Key 无效或已过期，请检查 .env 中的 MODEL_API_KEY")
            if resp.status_code == 402:
                raise RuntimeError("模型账户额度不足，请充值后重试")
            if resp.status_code == 429:
                last_err = RuntimeError("触发模型限流")
                if attempt < _MAX_RETRIES:
                    time.sleep(0.5 * (2**attempt))
                    continue
                raise RuntimeError("触发模型限流，请稍后重试")
            if resp.status_code >= 500:
                last_err = RuntimeError(f"模型接口返回 {resp.status_code}")
                if attempt < _MAX_RETRIES:
                    time.sleep(0.5 * (2**attempt))
                    continue
                raise last_err
            if resp.status_code >= 400:
                raise RuntimeError(f"模型接口返回 {resp.status_code}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except RuntimeError:
            raise  # 明确的业务错误直接抛出，不重试
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("Model request attempt failed: %s", type(e).__name__)
            if attempt < _MAX_RETRIES:
                time.sleep(0.5 * (2**attempt))
    raise RuntimeError(f"模型调用失败（已重试 {_MAX_RETRIES} 次）：{type(last_err).__name__}")


def chat_completion_stream(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 800,
):
    """流式调用 OpenAI 兼容接口，逐段 yield 文本增量（token 级别）。

    中途失败会抛异常，由调用方转为统一 error 事件；不静默断流。
    """
    if not is_configured():
        raise RuntimeError("未配置模型 API Key")
    url = f"{_base_url()}/chat/completions"
    payload: dict = {
        "model": _model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {settings.model_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code == 401:
                raise RuntimeError("API Key 无效或已过期，请检查 .env 中的 MODEL_API_KEY")
            if resp.status_code == 402:
                raise RuntimeError("模型账户额度不足，请充值后重试")
            if resp.status_code == 429:
                raise RuntimeError("触发模型限流，请稍后重试")
            if resp.status_code >= 400:
                raise RuntimeError(f"模型接口返回 {resp.status_code}")
            for line in resp.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                delta = (data.get("choices") or [{}])[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content


def _extract_json(text: str) -> str:
    """宽容地提取 JSON：模型可能包在 ```json``` 或前后有解释文字。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def extract_slots_llm(text: str, now) -> FishingContext | None:
    """LLM 槽位抽取；失败返回 None（由调用方回退到规则解析）。"""
    try:
        raw = chat_completion(
            [
                {"role": "system", "content": prompts.get_text("slot_system")},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=300,
            json_mode=True,
        )
        data = json.loads(_extract_json(raw))
        ctx = FishingContext(
            location=data.get("location") or None,
            target_species=data.get("target_species") or None,
            travel_radius=data.get("travel_radius") or None,
            water_type=data.get("water_type") or None,
            tackle=data.get("tackle") or None,
            constraints=[c for c in (data.get("constraints") or []) if isinstance(c, str)],
        )
        # 相对时间转绝对日期用确定性解析，不依赖模型算日期
        rule_ctx = intent_rules.extract_slots(text, now)
        ctx.time_window = rule_ctx.time_window
        ctx.time_label = rule_ctx.time_label
        ctx.start_iso = rule_ctx.start_iso
        ctx.end_iso = rule_ctx.end_iso
        return ctx
    except Exception:  # noqa: BLE001
        return None


PLAN_USER_TEMPLATE = """
{today_line}

提醒：方案数据里的 time_window / best_window 是绝对日期或时段。回复时必须把它们换算成"今天/明天/后天"，并且要与用户问的那一天保持一致：用户问今天就答今天，问明天才答明天；不要把今天说成明天，也不要建议已经过去的时间段。

下面是确定性决策引擎生成的方案数据。请将它转换为面向用户的出钓建议。

<plan_data>
{plan_json}
</plan_data>
""".strip()

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _today_line() -> str:
    now = datetime.now()
    return f"今天是 {now.year}年{now.month}月{now.day}日（{_WEEKDAYS[now.weekday()]}）。"


def generate_reply_llm(plan: PlanData) -> str:
    """基于方案数据生成自然语言回复。"""
    user = json.dumps(plan.model_dump(), ensure_ascii=False)
    raw = chat_completion(
        [
            {"role": "system", "content": prompts.get_text("reply_system")},
            {"role": "user", "content": PLAN_USER_TEMPLATE.format(plan_json=user, today_line=_today_line())},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return raw.strip()


def stream_reply(plan: PlanData):
    """流式生成回复（生成器）。

    - 安全 no_go：确定性文案，不调模型；
    - 未配置 Key：模板；
    - 已配置：逐 token 流式调用真实模型，异常向上抛由 api 层转 error。
    """
    if plan.conclusion == "no_go" and plan.safety:
        yield "⚠️ " + plan.safety[0]
        return
    if not is_configured():
        yield _template_reply(plan)
        return
    user = json.dumps(plan.model_dump(), ensure_ascii=False)
    yield from chat_completion_stream(
        [
            {"role": "system", "content": prompts.get_text("reply_system")},
            {"role": "user", "content": PLAN_USER_TEMPLATE.format(plan_json=user, today_line=_today_line())},
        ],
        temperature=0.3,
        max_tokens=300,
    )


# ---------- 对外回复（带兜底） ----------


def reply_for_clarify(missing: str) -> str:
    if missing == "location":
        return prompts.get_text("clarify_location")
    if missing == "target_species":
        return prompts.get_text("clarify_species")
    return prompts.get_text("clarify_generic")


def reply_for_plan(plan: PlanData) -> str:
    # 安全优先：no_go 时用确定性文案，不交给模型
    if plan.conclusion == "no_go" and plan.safety:
        return "⚠️ " + plan.safety[0]

    if is_configured():
        try:
            text = generate_reply_llm(plan)
            if text:
                return text
        except Exception:  # noqa: BLE001
            pass  # 回退模板
    return _template_reply(plan)


def _template_reply(plan: PlanData) -> str:
    conclusion_text = {"go": "建议去", "conditional": "可去但窗口短", "no_go": "不建议"}
    lines = []
    head = conclusion_text[plan.conclusion]
    if plan.conclusion == "conditional":
        head += f"，只抓 {plan.best_window or '关键窗口'}"
    head += f"（信心{'高' if plan.confidence=='high' else '中' if plan.confidence=='mid' else '低'}）"
    lines.append(head)

    if plan.best_window:
        lines.append(
            f"最佳窗口：{plan.best_window}"
            + (f"；备选：{plan.backup_window}" if plan.backup_window else "")
        )

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
    lines.append("下一步：跟老付说“改成下午/换目标鱼/改距离”，我只重算受影响的部分。")
    lines.append("合规提醒：出发前核实当地禁渔期、禁钓区，泥鳅活饵全禁，保护鱼种放流。")
    return "\n".join(lines)


def reply_for_knowledge(species: str) -> str:
    k = get_species(species)
    if not k:
        return "我还不太了解这种鱼，可以试试问翘嘴、鳜鱼、鲈鱼等常见淡水路亚对象鱼。"
    lures = "、".join(f"{l['type']}({l['weight']})" for l in k["lures"][:2])
    return (
        f"{species}：目标水层以{k['water_layer']}为主，活跃时段多在{k['prime_time']}，"
        f"常见标点有{'、'.join(k['spots'][:2])}。常用拟饵：{lures}。\n\n{_compliance_note()}"
    )


def reply_for_mistakes() -> str:
    """常见误区（确定性文案，来自知识库）。"""
    lines = [prompts.get_text("mistakes_intro")]
    for i, m in enumerate(prompts.get_list("common_mistakes"), 1):
        lines.append(f"{i}. {m}")
    lines.append(_compliance_note())
    return "\n".join(lines)


def reply_for_tips() -> str:
    """实操技巧（确定性文案，来自知识库）。"""
    lines = [prompts.get_text("tips_intro")]
    for i, t in enumerate(prompts.get_list("practical_tips"), 1):
        lines.append(f"{i}. {t}")
    lines.append(_compliance_note())
    return "\n".join(lines)


def reply_for_safety_rules() -> str:
    """安全与法规提醒（确定性文案，来自知识库）。"""
    lines = [prompts.get_text("safety_intro")]
    for i, r in enumerate(prompts.get_list("safety_rules"), 1):
        lines.append(f"{i}. {r}")
    return "\n".join(lines)


def reply_for_beginner() -> str:
    """新手入门速览：安全 + 技巧 + 误区。"""
    lines = ["老付带你入门，第一次钓鱼先记住这三条线："]
    lines.append("【安全】" + "；".join(prompts.get_list("safety_rules")) + "。")
    lines.append("【技巧】" + "；".join(prompts.get_list("practical_tips")) + "。")
    lines.append("【避坑】" + "；".join(prompts.get_list("common_mistakes")) + "。")
    lines.append(_compliance_note())
    return "\n".join(lines)


def reply_for_tackle(message: str) -> str:
    """装备/拟饵搭配建议（确定性规则 + 知识库）。"""
    # 1) 目标鱼 → 该鱼拟饵方案
    species = None
    for alias, name in SPECIES_ALIASES.items():
        if alias in message:
            species = name
            break
    if species:
        k = get_species(species)
        if k:
            lures = "、".join(f"{l['type']}({l['weight']})" for l in k["lures"][:3])
            technique = k.get("technique") or k["lures"][0]["action"]
            return (
                f"打{species}，老付推荐：{lures}。手法上{technique}，"
                f"标点优先{'、'.join(k['spots'][:2])}。口诀：{LURE_SELECTION_RULE}。\n\n{_compliance_note()}"
            )

    # 2) 竿调性 → 饵重范围 + 轮线搭配
    rod = tackle.parse_rod_action([message])
    if rod:
        lo, hi = tackle.ROD_WEIGHT_RANGE.get(rod, (0, 0))
        target = ROD_TARGET.get(rod, "泛用")
        lines = [
            f"{rod} 竿适合抛 {lo:g}–{hi:g}g 的饵，{target}。",
            REEL_GUIDE["纺车轮"],
            LINE_PAIRING,
            _compliance_note(),
        ]
        return "\n".join(lines)

    # 3) 通用 → 新手套装
    return _beginner_kit_reply() + "\n\n" + _compliance_note()


def _beginner_kit_reply() -> str:
    lines = [f"新手第一套，老付建议{BEGINNER_KIT['principle']}的通用组合："]
    lines.append(f"竿：{BEGINNER_KIT['rod']}")
    lines.append(f"轮：{BEGINNER_KIT['reel']}")
    lines.append(f"线：{BEGINNER_KIT['line']}")
    lines.append(f"饵：{BEGINNER_KIT['lure']}")
    lines.append(f"选型口诀：{LURE_SELECTION_RULE}")
    return "\n".join(lines)


def reply_out_of_scope(intent: str) -> str:
    if intent == "ON_SITE_TROUBLESHOOT":
        return "临场排障将在后续阶段开放。本阶段可先帮你规划出钓方案，告诉我时间、地点和目标鱼即可。"
    if intent == "CATCH_REVIEW":
        return "战报复盘将在后续阶段开放。本阶段可先帮你规划出钓方案。"
    return "这个问题暂未覆盖，你可以先问我“今天值得去吗”“去哪打翘嘴”等出钓决策问题。"


# ---------- 战报复盘（FR-07） ----------

REVIEW_USER_TEMPLATE = """
下面是用户战报及其关联计划数据。请生成一次克制、可验证的复盘。

<report_data>
{report_json}
</report_data>
""".strip()


def generate_review_llm(report: dict) -> str:
    user = json.dumps(report, ensure_ascii=False)
    raw = chat_completion(
        [
            {"role": "system", "content": prompts.get_text("review_system")},
            {"role": "user", "content": REVIEW_USER_TEMPLATE.format(report_json=user)},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return raw.strip()


def review_for_report(report: dict) -> str:
    if is_configured():
        try:
            text = generate_review_llm(report)
            if text:
                return text
        except Exception:  # noqa: BLE001
            pass
    return _template_review(report)


def _template_review(report: dict) -> str:
    label = report.get("result_label") or report.get("result_type") or "未知"
    parts = [f"本次结果：{label}。"]
    if report.get("species"):
        parts.append(f"目标鱼：{report['species']}。")
    if report.get("lure"):
        parts.append(f"用饵：{report['lure']}。")
    if report.get("length_weight"):
        parts.append(f"个体：{report['length_weight']}。")
    if report.get("water_color"):
        parts.append(f"水色：{report['water_color']}。")
    if report.get("flow"):
        parts.append(f"流速：{report['flow']}。")
    if label in ("空军", "skunked"):
        parts.append("可能因素：窗口、水层或标点与当天鱼情不匹配。下次优先对比低光窗口和风向再定标点，并保留记录以便校准。")
    else:
        parts.append("本次有效要素已记录，下次可在相似窗口和标点继续验证。")
    return "".join(parts)


# ---------- 个性化经验总结（第 3 阶段） ----------

INSIGHT_USER_TEMPLATE = """
下面是用户的战报统计数据。请生成个人规律总结和下次验证建议。

<stats_data>
{stats_json}
</stats_data>
""".strip()


def generate_insight_llm(stats: dict) -> str:
    user = json.dumps(stats, ensure_ascii=False)
    raw = chat_completion(
        [
            {"role": "system", "content": prompts.get_text("insight_system")},
            {"role": "user", "content": INSIGHT_USER_TEMPLATE.format(stats_json=user)},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return raw.strip()


def insight_for_stats(stats: dict) -> str:
    if is_configured():
        try:
            text = generate_insight_llm(stats)
            if text:
                return text
        except Exception:  # noqa: BLE001
            pass
    return _template_insight(stats)


def _template_insight(stats: dict) -> str:
    total = stats.get("total", 0)
    if total == 0:
        return "你还没有战报记录。去钓一场后，用“记一下今天的战报”告诉我结果，我就能帮你总结规律。"
    parts = [f"你共记录了 {total} 次战报。"]
    dist = stats.get("result_dist") or {}
    if dist:
        parts.append("结果分布：" + "、".join(f"{k}{v}次" for k, v in dist.items()) + "。")
    top = stats.get("top_species") or []
    if top:
        parts.append("常钓目标鱼：" + "、".join(f"{s['species']}({s['count']}次)" for s in top) + "。")
    parts.append("持续记录，我会越来越懂你的水情和鱼口规律。")
    return "".join(parts)
