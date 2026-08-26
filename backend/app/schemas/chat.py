"""请求 / 槽位 / 方案卡结构（Pydantic 强校验）。"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# 意图类型（对齐 PRD 10.1，本阶段主要覆盖前三种）
IntentType = Literal[
    "PLAN_TRIP",
    "GO_OR_NOT",
    "CHOOSE_TIME",
    "CHOOSE_PLACE",
    "TACKLE_ADVICE",
    "ON_SITE_TROUBLESHOOT",
    "CATCH_REVIEW",
    "KNOWLEDGE_QA",
    "SAFETY_OR_RULES",
    "FORECAST",
    "UNKNOWN",
]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None
    # 前端可回传已解析的上下文（用于纠正/补充）
    context: Optional[dict[str, Any]] = None


class FishingContext(BaseModel):
    """对话槽位（对齐 PRD 10.2）。"""

    location: Optional[str] = None
    lat: Optional[float] = None  # 精确定位纬度（WGS-84）
    lon: Optional[float] = None  # 精确定位经度（WGS-84）
    time_window: Optional[str] = None  # 原始文本，如"明早"
    time_label: Optional[str] = None  # 解析后的绝对表述，如"明天 05:00–09:00"
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    target_species: Optional[str] = None
    travel_radius: Optional[str] = None
    water_type: Optional[str] = None
    tackle: Optional[str] = None
    skill_level: str = "入门"
    constraints: list[str] = Field(default_factory=list)


class PlanDetail(BaseModel):
    """作钓方案模块。"""

    spot_type: Optional[str] = None  # 标点类型
    water_layer: Optional[str] = None  # 目标水层
    primary_lure: Optional[str] = None  # 主拟饵
    backup_lure: Optional[str] = None  # 备选拟饵
    weight_color: Optional[str] = None  # 克重/颜色
    action: Optional[str] = None  # 手法/节奏
    adjust_condition: Optional[str] = None  # 调整条件


class PlanData(BaseModel):
    """方案卡（对应决策卡字段，PRD 12 节）。"""

    session_id: Optional[str] = None
    version: int = 1
    location: Optional[str] = None
    time_window: Optional[str] = None
    target_species: Optional[str] = None
    travel_radius: Optional[str] = None
    conclusion: Literal["go", "conditional", "no_go"] = "conditional"
    confidence: Literal["high", "mid", "low"] = "mid"
    score: int = Field(ge=0, le=100)
    best_window: Optional[str] = None
    backup_window: Optional[str] = None
    factors: list[str] = Field(default_factory=list)
    plan_detail: PlanDetail = Field(default_factory=PlanDetail)
    risks: list[str] = Field(default_factory=list)
    safety: list[str] = Field(default_factory=list)
    data_basis: dict[str, Any] = Field(default_factory=dict)
    history_note: Optional[str] = None


class ChatDonePayload(BaseModel):
    type: Literal["reply", "plan", "clarify", "error"]
    reply: str = ""
    plan: Optional[PlanData] = None
    missing: list[str] = Field(default_factory=list)


class PlanCreateRequest(PlanData):
    pass
