"""对话编排状态机：计划 / 临场排障 / 战报复盘 三种流。

会话状态在进程内（短对话）；方案卡、战报、偏好持久化到 SQLite。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from ..core import db
from ..models.plan import Plan
from ..models.report import CatchReport
from ..schemas.chat import FishingContext, PlanData
from . import llm, onsite
from .decision import build_plan
from .intent import (
    SPECIES_ALIASES,
    detect_hazards,
    detect_intent,
    extract_slots,
    missing_slots,
)
from .profile import get_profile
from .weather import get_hourly

_BLOCKING_HAZARDS = {"雷暴", "暴雨", "大风", "洪水"}

# 会话状态（进程内）：session_id -> {"context","version","mode","pending"}
_sessions: dict[str, dict] = {}


def _get_or_create_session(session_id: str | None) -> tuple[str, dict]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    sid = session_id or uuid.uuid4().hex[:12]
    if sid not in _sessions:
        _sessions[sid] = {
            "context": FishingContext(),
            "version": 0,
            "mode": None,  # None | "onsite" | "report"
            "pending": {},
        }
    return sid, _sessions[sid]


def _merge(base: FishingContext, new: FishingContext) -> FishingContext:
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
    session["version"] += 1
    plan.version = session["version"]
    with db.get_session() as s:
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


_CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _num(s: str) -> int | None:
    if s.isdigit():
        return int(s)
    return _CN_NUM.get(s)


def _extract_count(text: str) -> int | None:
    m = re.search(r"([\d一二两三四五六七八九十]+)\s*[条尾个]", text)
    if m:
        return _num(m.group(1))
    return None


def _classify_result(text: str) -> str:
    if any(k in text for k in ["没去", "未出钓", "没出", "取消", "没钓成", "没去成"]):
        return "no_go"
    if any(k in text for k in ["上鱼", "中鱼", "钓到", "钓了", "爆护", "上岸", "中了"]):
        return "landed"
    if any(k in text for k in ["有口", "咬口", "咬不中", "只跟", "脱钩", "跑鱼"]):
        return "bite_no_fish"
    if any(k in text for k in ["空军", "没口", "白板", "没鱼", "龟了"]):
        return "skunked"
    return "skunked"


def _load_profile():
    with db.get_session() as s:
        return get_profile(s)


def extract_merged_slots(message: str, now: datetime | None = None) -> FishingContext:
    now = now or datetime.now()
    new_slots = extract_slots(message, now)
    if llm.is_configured() and (not new_slots.location or not new_slots.target_species):
        llm_slots = llm.extract_slots_llm(message, now)
        if llm_slots is not None:
            new_slots = _merge(new_slots, llm_slots)
    return new_slots


# ---------- 临场排障 ----------

def _handle_onsite_answer(message: str, sid: str, session: dict) -> dict:
    signal = onsite.classify_signal(message)
    session["mode"] = None
    return {
        "type": "onsite",
        "reply": onsite.steps_reply(signal),
        "steps": onsite.build_steps(signal),
        "session_id": sid,
    }


# ---------- 战报复盘 ----------

def _handle_report_input(message: str, sid: str, session: dict) -> dict:
    pending = session.get("pending") or {}

    # 已生成复盘，等待用户确认
    if pending.get("report_id"):
        if any(k in message for k in ["确认", "写入", "保存", "对", "是的", "好", "行"]):
            with db.get_session() as s:
                r = s.get(CatchReport, pending["report_id"])
                if r:
                    r.review_confirmed = True
                    s.commit()
            session["mode"] = None
            session["pending"] = {}
            return {"type": "reply", "reply": "已保存到你的战报历史。", "session_id": sid}
        if any(k in message for k in ["不", "取消", "算了", "别"]):
            session["mode"] = None
            session["pending"] = {}
            return {"type": "reply", "reply": "好的，这次不写入历史。", "session_id": sid}

    # 解析战报字段（结果类型 + 可选补充）
    result_type = _classify_result(message)
    species = _extract_species(message)
    count = _extract_count(message)

    ctx = session.get("context")
    inferred: dict = {}
    if ctx and ctx.target_species and not species:
        inferred["species"] = ctx.target_species
    if ctx and ctx.location:
        inferred["location"] = ctx.location

    plan_id = None
    with db.get_session() as s:
        last_plan = (
            s.query(Plan)
            .filter(Plan.session_id == sid, Plan.status == "active")
            .order_by(Plan.version.desc())
            .first()
        )
        plan_id = last_plan.id if last_plan else None

    with db.get_session() as s:
        rep = CatchReport(
            session_id=sid,
            plan_id=plan_id,
            result_type=result_type,
            species=species,
            count=count,
            inferred=inferred,
        )
        s.add(rep)
        s.commit()
        s.refresh(rep)
        report_dict = rep.to_dict()

    review = llm.review_for_report(report_dict)
    session["pending"] = {"report_id": report_dict["id"]}
    return {
        "type": "report",
        "reply": review + "\n\n要写入你的战报历史吗？（回复：确认 / 取消）",
        "report": report_dict,
        "session_id": sid,
    }


# ---------- 主流程 ----------

def prepare(message: str, session_id: str | None, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    sid, session = _get_or_create_session(session_id)
    intent = detect_intent(message)
    hazards = detect_hazards(message)
    mode = session.get("mode")

    # 模式优先：排障 / 战报的后续输入
    if mode == "onsite":
        return _handle_onsite_answer(message, sid, session)
    if mode == "report":
        return _handle_report_input(message, sid, session)

    # 进入排障流
    if intent == "ON_SITE_TROUBLESHOOT":
        session["mode"] = "onsite"
        return {
            "type": "clarify",
            "reply": onsite.ask_diagnostic_question(),
            "quick_options": ["完全没口", "有炸水但打不到", "有跟口不咬", "频繁挂底", "跑鱼"],
            "session_id": sid,
        }

    # 进入战报流
    if intent == "CATCH_REVIEW":
        session["mode"] = "report"
        session["pending"] = {}
        return {
            "type": "clarify",
            "reply": "记一下今天的结果，选一个：上鱼 / 有口未中 / 空军 / 未出钓",
            "quick_options": ["上鱼", "有口未中", "空军", "未出钓"],
            "session_id": sid,
        }

    # 知识问答
    if intent == "KNOWLEDGE_QA":
        species = _extract_species(message)
        if species:
            return {"type": "reply", "reply": llm.reply_for_knowledge(species), "session_id": sid}
        return {"type": "reply", "reply": "可以问我“翘嘴怎么钓”“鳜鱼在什么水层”等对象鱼知识。", "session_id": sid}

    # 法规类：本阶段未接入完整法规库
    if intent == "SAFETY_OR_RULES" and not hazards:
        return {
            "type": "reply",
            "reply": "完整禁钓/法规库本阶段暂未接入，出钓前请以现场告示为准；雷暴、大风、暴雨等天气风险我可以帮你判断。",
            "session_id": sid,
        }

    # 决策流：抽取并合并槽位
    new_slots = extract_merged_slots(message, now)
    ctx = _merge(session["context"], new_slots)
    session["context"] = ctx

    profile = _load_profile()
    blocking = [h for h in hazards if h in _BLOCKING_HAZARDS]

    # 高风险优先：跳过追问，立即给出安全结论
    if blocking:
        weather = get_hourly(ctx.location, now)
        plan = build_plan(ctx, weather, hazards, now, profile)
        plan.session_id = sid
        plan = _persist_plan(plan, session)
        return {"type": "plan", "reply": None, "plan": plan, "session_id": sid}

    missing = missing_slots(ctx)
    if missing:
        top = missing[0]
        return {"type": "clarify", "reply": llm.reply_for_clarify(top), "missing": [top], "session_id": sid}

    # 生成方案
    weather = get_hourly(ctx.location, now)
    plan = build_plan(ctx, weather, hazards, now, profile)
    plan.session_id = sid
    plan = _persist_plan(plan, session)
    return {"type": "plan", "reply": None, "plan": plan, "session_id": sid}


def handle(message: str, session_id: str | None, now: datetime | None = None) -> dict:
    """非流式入口：prepare + 补全回复（测试/冒烟用）。"""
    result = prepare(message, session_id, now)
    if result.get("plan") and result.get("reply") is None:
        result["reply"] = llm.reply_for_plan(result["plan"])
    return result
