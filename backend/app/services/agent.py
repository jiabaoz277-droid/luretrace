"""对话编排状态机：收集槽位 → 追问缺口 → 生成方案 → 持久化（版本化）。

本阶段会话槽位在进程内保存（短对话）；生成的方案卡持久化到 SQLite，可恢复。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from ..core import db
from ..models.plan import Plan
from ..schemas.chat import FishingContext, PlanData
from . import llm
from .decision import build_plan
from .intent import (
    SPECIES_ALIASES,
    detect_hazards,
    detect_intent,
    extract_slots,
    missing_slots,
)
from .weather import get_hourly

_BLOCKING_HAZARDS = {"雷暴", "暴雨", "大风", "洪水"}

# 会话状态（进程内）：session_id -> {"context": FishingContext, "version": int}
_sessions: dict[str, dict] = {}


def _get_or_create_session(session_id: str | None) -> tuple[str, dict]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    sid = session_id or uuid.uuid4().hex[:12]
    if sid not in _sessions:
        _sessions[sid] = {"context": FishingContext(), "version": 0}
    return sid, _sessions[sid]


def _merge(base: FishingContext, new: FishingContext) -> FishingContext:
    """只覆盖新句提供的非空字段；约束列表追加去重。"""
    data = base.model_dump()
    incoming = new.model_dump()
    for k, v in incoming.items():
        if k == "constraints":
            merged = list(dict.fromkeys(data.get("constraints", []) + (v or [])))
            data["constraints"] = merged
        elif v not in (None, "", []):
            data[k] = v
    return FishingContext(**data)


def _persist_plan(plan: PlanData, session: dict) -> PlanData:
    """版本化保存：旧 active 置为 outdated，新 plan 版本 +1。"""
    session["version"] += 1
    plan.version = session["version"]

    with db.get_session() as s:
        # 旧方案标记失效
        old = (
            s.query(Plan)
            .filter(Plan.session_id == plan.session_id, Plan.status == "active")
            .all()
        )
        for p in old:
            p.status = "outdated"
        row = Plan(
            session_id=plan.session_id,
            version=plan.version,
            location=plan.location,
            time_window=plan.time_window,
            target_species=plan.target_species,
            travel_radius=plan.travel_radius,
            conclusion=plan.conclusion,
            confidence=plan.confidence,
            score=plan.score,
            best_window=plan.best_window,
            backup_window=plan.backup_window,
            factors=plan.factors,
            plan_detail=plan.plan_detail.model_dump(),
            risks=plan.risks,
            safety=plan.safety,
            data_basis=plan.data_basis,
            status="active",
        )
        s.add(row)
        s.commit()
    return plan


def _extract_species(text: str) -> str | None:
    for alias, species in SPECIES_ALIASES.items():
        if alias in text:
            return species
    return None


def handle(message: str, session_id: str | None, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    sid, session = _get_or_create_session(session_id)
    intent = detect_intent(message)
    hazards = detect_hazards(message)

    # 知识问答：直接回答，不进决策流
    if intent == "KNOWLEDGE_QA":
        species = _extract_species(message)
        if species:
            return {"type": "reply", "reply": llm.reply_for_knowledge(species), "session_id": sid}
        return {"type": "reply", "reply": "可以问我“翘嘴怎么钓”“鳜鱼在什么水层”等对象鱼知识。", "session_id": sid}

    # 阶段外能力：明确告知
    if intent in ("ON_SITE_TROUBLESHOOT", "CATCH_REVIEW"):
        return {"type": "reply", "reply": llm.reply_out_of_scope(intent), "session_id": sid}

    # 法规类：本阶段未接入完整法规库
    if intent == "SAFETY_OR_RULES" and not hazards:
        return {
            "type": "reply",
            "reply": "完整禁钓/法规库本阶段暂未接入，出钓前请以现场告示为准；雷暴、大风、暴雨等天气风险我可以帮你判断。",
            "session_id": sid,
        }

    # 决策流：规则抽取 +（已配置时）LLM 抽取，LLM 非空字段优先、规则兑底
    new_slots = extract_slots(message, now)
    if llm.is_configured():
        llm_slots = llm.extract_slots_llm(message, now)
        if llm_slots is not None:
            new_slots = _merge(new_slots, llm_slots)
    ctx = _merge(session["context"], new_slots)
    session["context"] = ctx

    # 高风险优先：跳过追问，立即给出安全结论
    blocking = [h for h in hazards if h in _BLOCKING_HAZARDS]
    if blocking:
        weather = get_hourly(ctx.location, now)
        plan = build_plan(ctx, weather, hazards, now)
        plan.session_id = sid
        plan = _persist_plan(plan, session)
        return {"type": "plan", "reply": llm.reply_for_plan(plan), "plan": plan, "session_id": sid}

    missing = missing_slots(ctx)
    if missing:
        top = missing[0]
        return {"type": "clarify", "reply": llm.reply_for_clarify(top), "missing": [top], "session_id": sid}

    # 生成方案
    weather = get_hourly(ctx.location, now)
    plan = build_plan(ctx, weather, hazards, now)
    plan.session_id = sid
    plan = _persist_plan(plan, session)
    return {"type": "plan", "reply": llm.reply_for_plan(plan), "plan": plan, "session_id": sid}
