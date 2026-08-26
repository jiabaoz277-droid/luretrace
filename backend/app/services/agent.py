"""对话编排状态机：计划 / 临场排障 / 战报复盘 三种流。

会话状态在进程内（短对话）；方案卡、战报、偏好持久化到 SQLite。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from ..core import db
from ..core.validation import validate_plan
from ..models.plan import Plan
from ..models.report import RESULT_LABELS, CatchReport
from ..models.spot import FavoriteSpot
from ..schemas.chat import FishingContext, PlanData
from . import forecast, insights, llm, onsite, waters
from . import geo
from .decision import build_plan
from .intent import (
    SPECIES_ALIASES,
    detect_hazards,
    detect_intent,
    extract_slots,
    missing_slots,
)
from .knowledge import BANNED_EQUIPMENT, recommend_species, region_for_province
from .profile import get_profile
from .weather import get_hourly

_BLOCKING_HAZARDS = {"雷暴", "暴雨", "大风", "洪水"}

# 会话状态（进程内）：key = user_id:session_id，避免跨用户串状态
_sessions: dict[str, dict] = {}


def _session_key(user_id: str, sid: str) -> str:
    return f"{user_id}:{sid}"


def _get_or_create_session(user_id: str, session_id: str | None) -> tuple[str, dict]:
    sid = session_id or uuid.uuid4().hex[:12]
    key = _session_key(user_id, sid)
    if key in _sessions:
        return sid, _sessions[key]
    _sessions[key] = {
        "context": FishingContext(),
        "version": 0,
        "mode": None,  # None | "onsite" | "report"
        "pending": {},
        "completed": False,
    }
    return sid, _sessions[key]


_NEW_TASK_HINTS = [
    "值得去", "能去吗", "可以去吗", "适不适合", "要不要去", "能钓吗", "行不行",
    "给个方案", "什么时候去", "去哪", "哪里", "哪个地方", "什么地方",
    "未来几天", "这周", "周末", "明天", "后天", "几点", "什么时候",
]


def _starts_new_task(text: str) -> bool:
    """新输入是否开启一个新出钓任务（而非回答上一任务的追问）。"""
    return any(k in text for k in _NEW_TASK_HINTS)


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


def _persist_plan(plan: PlanData, session: dict, user_id: str) -> PlanData:
    session["version"] += 1
    plan.version = session["version"]
    session["completed"] = True
    with db.get_session() as s:
        old = (
            s.query(Plan)
            .filter(
                Plan.session_id == plan.session_id,
                Plan.user_id == user_id,
                Plan.status == "active",
            )
            .all()
        )
        for p in old:
            p.status = "outdated"
        row = Plan(
            user_id=user_id,
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
            history_note=plan.history_note,
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


def _extract_lure(text: str) -> str | None:
    lures = ["沉水铅笔", "铅头钩", "亮片", "米诺", "铅笔", "波爬", "雷蛙", "铁板", "德州", "倒吊", "软饵", "软虫", "胖子", "crank", "VIB", "vib"]
    hits = [l for l in lures if l in text.lower()]
    return "、".join(hits) if hits else None


def _extract_length_weight(text: str) -> str | None:
    m = re.search(r"[\d一二两三四五六七八九十]+\s*[斤两]|\d+\s*(?:公分|厘米|cm|CM)", text)
    return m.group(0) if m else None


def _extract_water_color(text: str) -> str | None:
    for kw in ["浑", "清", "黄", "绿"]:
        if kw in text:
            return kw
    return None


def _extract_flow(text: str) -> str | None:
    for kw in ["急流", "缓流", "静水", "走水", "流水"]:
        if kw in text:
            return kw
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


def _load_profile(user_id: str):
    with db.get_session() as s:
        return get_profile(s, user_id)


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
    ctx = onsite.extract_onsite_context(message)
    return {
        "type": "onsite",
        "reply": onsite.steps_reply(signal, ctx),
        "steps": onsite.build_steps(signal),
        "session_id": sid,
    }


# ---------- 战报复盘 ----------

def _handle_report_input(message: str, sid: str, session: dict, user_id: str) -> dict:
    pending = session.get("pending") or {}

    # 已生成复盘，等待用户确认
    if pending.get("report_id"):
        if any(k in message for k in ["确认", "写入", "保存", "对", "是的", "好", "行"]):
            with db.get_session() as s:
                r = s.get(CatchReport, pending["report_id"])
                if r and r.user_id == user_id:
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
    lure = _extract_lure(message)
    length_weight = _extract_length_weight(message)
    water_color = _extract_water_color(message)
    flow = _extract_flow(message)

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
            .filter(Plan.session_id == sid, Plan.user_id == user_id, Plan.status == "active")
            .order_by(Plan.version.desc())
            .first()
        )
        plan_id = last_plan.id if last_plan else None

    with db.get_session() as s:
        rep = CatchReport(
            user_id=user_id,
            session_id=sid,
            plan_id=plan_id,
            result_type=result_type,
            species=species,
            count=count,
            lure=lure,
            length_weight=length_weight,
            water_color=water_color,
            flow=flow,
            note=message,
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


# ---------- 收藏钓点 / 个性化经验（第 3 阶段） ----------

def _similar_history(target_species: str | None, user_id: str) -> str | None:
    if not target_species:
        return None
    with db.get_session() as s:
        r = (
            s.query(CatchReport)
            .filter(CatchReport.species == target_species, CatchReport.user_id == user_id)
            .order_by(CatchReport.id.desc())
            .first()
        )
    if not r:
        return None
    label = RESULT_LABELS.get(r.result_type, r.result_type)
    date_str = r.created_at.strftime("%m月%d日") if r.created_at else ""
    return f"历史参考：你上次打{target_species}（{date_str}）是{label}。"


def _list_favorites(sid: str, user_id: str) -> dict:
    with db.get_session() as s:
        spots = (
            s.query(FavoriteSpot)
            .filter(FavoriteSpot.user_id == user_id)
            .order_by(FavoriteSpot.id.desc())
            .all()
        )
    if not spots:
        return {"type": "reply", "reply": "你还没有收藏钓点，说“收藏富春江”即可收藏。", "session_id": sid}
    names = "、".join(sp.name for sp in spots)
    favs = [
        {
            "name": sp.name,
            "spot_type": "收藏钓点",
            "reason": "你收藏的钓点",
            "lat": sp.lat,
            "lon": sp.lon,
            "distance_km": 0,
        }
        for sp in spots
        if sp.lat is not None and sp.lon is not None
    ]
    result: dict = {"type": "reply", "reply": f"你收藏了：{names}", "session_id": sid}
    if favs:
        result["spots"] = favs
    return result


def _add_favorite(message: str, sid: str, session: dict, now: datetime, user_id: str) -> dict:
    loc = extract_slots(message, now).location
    if not loc:
        loc = session["context"].location
    if not loc:
        return {"type": "reply", "reply": "想收藏哪个水域？告诉我名字，比如“收藏富春江”。", "session_id": sid}
    # 尽力地理编码拿坐标（用于地图展示；城市级反查，无坐标也能收藏）
    lat = lon = None
    place = geo.lookup_location(loc)
    if place and place.get("lat") and place.get("lon"):
        try:
            lat, lon = float(place["lat"]), float(place["lon"])
        except (TypeError, ValueError):
            lat = lon = None
    with db.get_session() as s:
        spot = FavoriteSpot(user_id=user_id, name=loc, location=loc, lat=lat, lon=lon)
        s.add(spot)
        s.commit()
    return {"type": "reply", "reply": f"已收藏「{loc}」。", "session_id": sid}


def _handle_insight(sid: str, user_id: str) -> dict:
    with db.get_session() as s:
        stats = insights.compute(s, user_id)
    return {"type": "insight", "reply": llm.insight_for_stats(stats), "insight": stats, "session_id": sid}


def _spots_reply(place: str, spots: list[dict]) -> str:
    """把地图水域分析出的候选钓点整理成老付式回复。"""
    lines = [f"老付看了下 {place} 附近的水域，给你几个大概率有口的点："]
    for i, s in enumerate(spots, 1):
        lines.append(
            f"{i}. {s['name']}·{s['spot_type']}（距你约 {s['distance_km']} 公里）\n"
            f"   {s['reason']}。"
        )
    lines.append("建议挑清晨或傍晚的低光窗口去；告诉我目标鱼，我再细化用饵和手法。")
    lines.append("出发前核实当地禁渔期、禁钓区和保护鱼种，不确定能否作钓的水域别下竿。")
    return "\n".join(lines)


# ---------- 主流程 ----------

def prepare(
    message: str,
    session_id: str | None,
    now: datetime | None = None,
    context: dict | None = None,
    user_id: str = "default",
) -> dict:
    now = now or datetime.now()
    sid, session = _get_or_create_session(user_id, session_id)

    # 前端传来的精确定位（浏览器 GPS/WiFi 坐标，WGS-84）
    if context and context.get("lat") is not None and context.get("lon") is not None:
        session["context"].lat = float(context["lat"])
        session["context"].lon = float(context["lon"])

    intent = detect_intent(message)
    primary = intent.primary_intent
    hazards = detect_hazards(message)
    mode = session.get("mode")

    # 模式优先：排障 / 战报的后续输入
    if mode == "onsite":
        return _handle_onsite_answer(message, sid, session)
    if mode == "report":
        return _handle_report_input(message, sid, session, user_id)

    # 装备/钓法合规问答（三本钩、泥鳅活饵、串钩等）
    if any(k in message for k in ["能不能", "可以吗", "合法吗", "允许", "违规", "禁用", "能用吗", "行不行"]):
        for eq, guidance in BANNED_EQUIPMENT.items():
            if eq in message:
                return {"type": "reply", "reply": f"老付说下「{eq}」：{guidance}", "session_id": sid}

    # 收藏 / 历史规律（第 3 阶段）
    if "收藏" in message:
        if any(k in message for k in ["我的收藏", "收藏了", "收藏的", "看收藏"]):
            return _list_favorites(sid, user_id)
        return _add_favorite(message, sid, session, now, user_id)
    if any(k in message for k in ["我的规律", "历史规律", "复盘总结", "我的战报", "历史总结"]):
        return _handle_insight(sid, user_id)

    # 进入排障流
    if primary == "ON_SITE_TROUBLESHOOT":
        if onsite.has_explicit_signal(message):
            # 已明确信号：直接给步骤，不再追问信号类型
            signal = onsite.classify_signal(message)
            session["mode"] = None
            ctx = onsite.extract_onsite_context(message)
            return {
                "type": "onsite",
                "reply": onsite.steps_reply(signal, ctx),
                "steps": onsite.build_steps(signal),
                "session_id": sid,
            }
        session["mode"] = "onsite"
        return {
            "type": "clarify",
            "reply": onsite.ask_diagnostic_question(),
            "quick_options": ["完全没口", "有炸水但打不到", "有跟口不咬", "频繁挂底", "跑鱼"],
            "session_id": sid,
        }

    # 进入战报流
    if primary == "CATCH_REPORT":
        session["mode"] = "report"
        session["pending"] = {}
        return {
            "type": "clarify",
            "reply": "记一下今天的结果，选一个：上鱼 / 有口未中 / 空军 / 未出钓",
            "quick_options": ["上鱼", "有口未中", "空军", "未出钓"],
            "session_id": sid,
        }

    # 知识问答
    if primary == "KNOWLEDGE_QA":
        species = _extract_species(message)
        if species:
            return {"type": "reply", "reply": llm.reply_for_knowledge(species), "session_id": sid}
        if any(k in message for k in ["新手", "入门", "第一次"]):
            return {"type": "reply", "reply": llm.reply_for_beginner(), "session_id": sid}
        if any(k in message for k in ["误区", "避坑", "注意什么"]):
            return {"type": "reply", "reply": llm.reply_for_mistakes(), "session_id": sid}
        if any(k in message for k in ["技巧", "手法", "操作"]):
            return {"type": "reply", "reply": llm.reply_for_tips(), "session_id": sid}
        return {"type": "reply", "reply": "可以问我“翘嘴怎么钓”“鳜鱼在什么水层”等对象鱼知识。", "session_id": sid}

    # 装备/拟饵搭配（纯装备问答，无出钓计划语义）
    if primary == "TACKLE_QA":
        return {"type": "reply", "reply": llm.reply_for_tackle(message), "session_id": sid}

    # 多日出钓预报（作为出钓计划的次意图）
    if primary == "PLAN_TRIP" and "FORECAST" in intent.secondary_intents:
        ctx = session["context"]
        loc = extract_slots(message, now).location or ctx.location
        if not loc and ctx.lat is not None and ctx.lon is not None:
            rev = geo.reverse_lookup(ctx.lat, ctx.lon)
            loc = (rev or {}).get("name") or (rev or {}).get("district")
        if not loc:
            return {
                "type": "clarify",
                "reply": llm.reply_for_clarify("location"),
                "missing": ["location"],
                "session_id": sid,
            }
        return {"type": "reply", "reply": forecast.forecast_reply(loc), "session_id": sid}

    # 近场钓点推荐（作为出钓计划的次意图）
    if primary == "PLAN_TRIP" and "CHOOSE_PLACE" in intent.secondary_intents:
        ctx = session["context"]
        loc = extract_slots(message, now).location or ctx.location
        # 有精确定位优先用坐标，否则用地点名反查
        if ctx.lat is not None and ctx.lon is not None:
            spots = waters.find_spots(lat=ctx.lat, lon=ctx.lon)
            place_label = loc or "你定位的位置"
        elif loc:
            spots = waters.find_spots(place=loc)
            place_label = loc
        else:
            return {
                "type": "clarify",
                "reply": llm.reply_for_clarify("location"),
                "missing": ["location"],
                "session_id": sid,
            }
        if spots:
            return {"type": "reply", "reply": _spots_reply(place_label, spots), "spots": spots, "session_id": sid}
        return {
            "type": "reply",
            "reply": (
                f"{place_label}附近的水域数据老付暂时没查到，先给你通用思路：找入水口、回水湾、深浅交界。"
                f"也可以直接说“明早{place_label}打翘嘴”，我出完整方案。"
            ),
            "session_id": sid,
        }

    # 法规类：本阶段未接入完整法规库
    if primary == "SAFETY_STOP" and not hazards:
        return {
            "type": "reply",
            "reply": "完整禁钓/法规库本阶段暂未接入，出钓前请以现场告示为准；雷暴、大风、暴雨等天气风险我可以帮你判断。\n\n" + llm.reply_for_safety_rules(),
            "session_id": sid,
        }

    # 任务切换：上一任务已完成，新输入开启新任务 → 重置累积槽位，避免悄悄沿用旧鱼种/地点
    if session.get("completed") and _starts_new_task(message):
        session["context"] = FishingContext()
        session["version"] = 0
        session["completed"] = False
        session["pending"] = {}

    # 决策流：抽取并合并槽位
    new_slots = extract_merged_slots(message, now)
    ctx = _merge(session["context"], new_slots)
    session["context"] = ctx

    profile = _load_profile(user_id)
    blocking = [h for h in hazards if h in _BLOCKING_HAZARDS]

    # 高风险优先：跳过追问，立即给出安全结论
    if blocking:
        weather = get_hourly(ctx.location, now)
        plan = build_plan(ctx, weather, hazards, now, profile)
        plan.session_id = sid
        plan.history_note = _similar_history(plan.target_species, user_id)
        plan = _persist_plan(plan, session, user_id)
        return {"type": "plan", "reply": None, "plan": plan, "session_id": sid}

    missing = missing_slots(ctx)
    if missing:
        return {
            "type": "clarify",
            "reply": llm.reply_for_clarify(missing[0]),
            "missing": [missing[0]],
            "session_id": sid,
        }

    # 用户明确问“钓什么鱼”→ 按季节+地域推荐候选（PRD 10.2 可给候选）
    if any(k in message for k in ["钓什么鱼", "什么鱼", "打什么", "钓啥"]):
        region = "全国"
        if ctx.location:
            place = geo.lookup_location(ctx.location)
            if place and place.get("adm1"):
                region = region_for_province(place["adm1"])
        candidates = recommend_species(now.month, region)
        where = ctx.location or "这个季节"
        reply = f"{where} {now.month} 月适合打：{'、'.join(candidates)}，选一个我帮你出方案。"
        return {
            "type": "clarify",
            "reply": reply,
            "missing": ["target_species"],
            "quick_options": candidates,
            "session_id": sid,
        }

    # 生成方案
    weather = get_hourly(ctx.location, now)
    plan = build_plan(ctx, weather, hazards, now, profile)
    issues = validate_plan(plan, ctx)
    if any(i.severity == "error" for i in issues):
        plan.confidence = "low"
        plan.risks.append("方案一致性校验未通过，已给出保守建议")
    plan.session_id = sid
    plan.history_note = _similar_history(plan.target_species, user_id)
    plan = _persist_plan(plan, session, user_id)
    return {"type": "plan", "reply": None, "plan": plan, "session_id": sid}


def handle(
    message: str,
    session_id: str | None,
    now: datetime | None = None,
    user_id: str = "default",
) -> dict:
    """非流式入口：prepare + 补全回复（测试/冒烟用）。"""
    result = prepare(message, session_id, now, user_id=user_id)
    if result.get("plan") and result.get("reply") is None:
        result["reply"] = llm.reply_for_plan(result["plan"])
    return result
