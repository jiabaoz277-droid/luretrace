"""模型抽象层：真实 LLM（OpenAI 兼容接口）优先，规则/模板兜底。

- 已配置 Key：槽位抽取 + 自然语言回复走真实模型；决策引擎仍为确定性规则。
- 未配置 Key 或调用失败：自动回退到确定性规则解析 + 模板回复，不影响核心链路。
- 安全提示永远由确定性代码保证，不交给模型决定（安全优先于鱼口）。
"""
from __future__ import annotations

import json
import re

import httpx

from ..core.config import settings
from ..schemas.chat import FishingContext, PlanData
from . import intent as intent_rules
from . import tackle
from .knowledge import (
    BEGINNER_KIT,
    COMMON_MISTAKES,
    LINE_GUIDE,
    LINE_PAIRING,
    LURE_SELECTION_RULE,
    PRACTICAL_TIPS,
    REEL_GUIDE,
    ROD_TARGET,
    SAFETY_RULES,
    SPECIES_ALIASES,
    get_species,
)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
_TIMEOUT = 30.0
_MAX_RETRIES = 2


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
    for _ in range(_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 401:
                raise RuntimeError("API Key 无效或已过期，请检查 .env 中的 MODEL_API_KEY")
            if resp.status_code == 402:
                raise RuntimeError("模型账户额度不足，请充值后重试")
            if resp.status_code == 429:
                raise RuntimeError("触发模型限流，请稍后重试")
            if resp.status_code >= 400:
                raise RuntimeError(f"模型接口返回 {resp.status_code}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except RuntimeError:
            raise  # 明确的业务错误直接抛出，不重试
        except Exception as e:  # noqa: BLE001
            last_err = e
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


_SLOT_SYSTEM = """你是"路亚问问"的槽位抽取器。从用户输入中抽取字段，只输出一个 JSON 对象，不要输出任何解释。
字段规则（找不到就填 null 或 []）：
- location: 出发城市或水域名，如 "杭州"、"富春江"
- target_species: 目标鱼规范名（常见淡水鱼：翘嘴/鳜鱼/鲈鱼/黑鱼/马口/白条/红尾/青稍/军鱼/罗非/鳡鱼/狗鱼/虹鳟/太阳鱼/白鲳/赤眼鳟/鲮鱼/鳊鱼/草鱼/鲤鱼/鲫鱼/鲶鱼/黄颡鱼/鲢鳙），口语要归一化到这些规范名
- travel_radius: 出行限制，如 "2小时"、"40公里"
- water_type: 江河/水库/湖泊/溪流
- tackle: 装备原文（竿调、拟饵等），如 "ML竿、7g亮片"
- constraints: 限制条件数组，如 ["不夜钓","带孩子"]
- time_raw: 时间原文，如 "明早5点到9点"

示例：
输入："明早杭州周边两小时，想打翘嘴"
输出：{"location":"杭州","target_species":"翘嘴","travel_radius":"2小时","water_type":null,"tackle":null,"constraints":[],"time_raw":"明早"}
输入："我只有ML竿和7g亮片，不夜钓"
输出：{"location":null,"target_species":null,"travel_radius":null,"water_type":null,"tackle":"ML竿、7g亮片","constraints":["不夜钓"],"time_raw":null}
"""


def extract_slots_llm(text: str, now) -> FishingContext | None:
    """LLM 槽位抽取；失败返回 None（由调用方回退到规则解析）。"""
    try:
        raw = chat_completion(
            [
                {"role": "system", "content": _SLOT_SYSTEM},
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


_REPLY_SYSTEM = """你是"老付"，一位拥有多年野钓实战经验的资深路亚玩家，随和接地气、说话通俗易懂，偶尔分享真实野钓趣事，精通淡水路亚、鱼种、钓点、装备与法规。回答规则：
1. 先结论后依据：先回答是否建议出钓、信心等级、最佳窗口。
2. 事实、推断、建议分层：天气是事实，鱼口是概率，动作是建议。
3. 只使用我提供的方案数据，绝不编造天气、钓点状态、法规或鱼情。
4. 不承诺"必中鱼""爆护"等确定性结果。
5. 简短可执行，正文不超过 120 字。
6. 主动宣传合规垂钓：不电鱼、不毒鱼、不放生外来入侵鱼种、小鱼放流、带走垂钓垃圾。
7. 纯文本输出，不要用 Markdown 符号（如 **、#、-、`）。
"""


def generate_reply_llm(plan: PlanData) -> str:
    """基于方案数据生成自然语言回复。"""
    user = json.dumps(plan.model_dump(), ensure_ascii=False)
    raw = chat_completion(
        [
            {"role": "system", "content": _REPLY_SYSTEM},
            {
                "role": "user",
                "content": f"根据以下方案数据，生成给用户的一句话回复（结论、窗口、方案要点）：\n{user}",
            },
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
            {"role": "system", "content": _REPLY_SYSTEM},
            {
                "role": "user",
                "content": f"根据以下方案数据，生成给用户的一句话回复（结论、窗口、方案要点）：\n{user}",
            },
        ],
        temperature=0.3,
        max_tokens=300,
    )


# ---------- 对外回复（带兜底） ----------


def reply_for_clarify(missing: str) -> str:
    if missing == "location":
        return "老付问你从哪出发？直接说城市或水域，或者授权当前位置也行。"
    if missing == "target_species":
        return "想打什么鱼？翘嘴、鳜鱼、鲈鱼都行，直接回鱼名。"
    return "还差点信息，补一下老付就给你出方案。"


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
        f"常见标点有{'、'.join(k['spots'][:2])}。常用拟饵：{lures}。"
    )


def reply_for_mistakes() -> str:
    """常见误区（确定性文案，来自知识库）。"""
    lines = ["老付跟你说几个新手常踩的误区："]
    for i, m in enumerate(COMMON_MISTAKES, 1):
        lines.append(f"{i}. {m}")
    return "\n".join(lines)


def reply_for_tips() -> str:
    """实操技巧（确定性文案，来自知识库）。"""
    lines = ["老付再给你几个实操技巧："]
    for i, t in enumerate(PRACTICAL_TIPS, 1):
        lines.append(f"{i}. {t}")
    return "\n".join(lines)


def reply_for_safety_rules() -> str:
    """安全与法规提醒（确定性文案，来自知识库）。"""
    lines = ["老付的安全与法规提醒："]
    for i, r in enumerate(SAFETY_RULES, 1):
        lines.append(f"{i}. {r}")
    return "\n".join(lines)


def reply_for_beginner() -> str:
    """新手入门速览：安全 + 技巧 + 误区。"""
    lines = ["老付带你入门，第一次钓鱼先记住这三条线："]
    lines.append("【安全】" + "；".join(SAFETY_RULES) + "。")
    lines.append("【技巧】" + "；".join(PRACTICAL_TIPS) + "。")
    lines.append("【避坑】" + "；".join(COMMON_MISTAKES) + "。")
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
                f"标点优先{'、'.join(k['spots'][:2])}。口诀：{LURE_SELECTION_RULE}。"
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
        ]
        return "\n".join(lines)

    # 3) 通用 → 新手套装
    return _beginner_kit_reply()


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

_REVIEW_SYSTEM = """你是"老付"在帮钓友复盘。基于用户战报和关联计划，生成简短复盘：
1. 哪些判断被验证、哪些可能失效；
2. 下次优先尝试什么；
3. 只使用提供的数据，不编造，不承诺"必中"；
4. 语气像老朋友聊天，不超过 80 字。"""


def generate_review_llm(report: dict) -> str:
    user = json.dumps(report, ensure_ascii=False)
    raw = chat_completion(
        [
            {"role": "system", "content": _REVIEW_SYSTEM},
            {"role": "user", "content": f"根据以下战报生成复盘：\n{user}"},
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

_INSIGHT_SYSTEM = """你是"老付"在帮钓友总结个人规律。基于用户战报统计，生成简短总结：
1. 结果分布与常钓目标鱼；
2. 只使用提供的数据，不编造；
3. 给出一个下次优先尝试的建议；
4. 语气随和接地气，不超过 100 字。"""


def generate_insight_llm(stats: dict) -> str:
    user = json.dumps(stats, ensure_ascii=False)
    raw = chat_completion(
        [
            {"role": "system", "content": _INSIGHT_SYSTEM},
            {"role": "user", "content": f"根据以下战报统计生成个性化总结：\n{user}"},
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
