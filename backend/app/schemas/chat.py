"""请求 / 槽位 / 方案卡结构（Pydantic 强校验）。

V1.2 改版：意图从单标签升级为「主意图 + 次意图 + 证据」；槽位增加硬约束字段；
方案卡增加数据完整度与条件档位，分离「条件分数」与「信心」。
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# 旧版意图枚举（向后兼容，deprecated；新逻辑请用 PrimaryIntent）
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

# 新版主意图（V1.2）
PrimaryIntent = Literal[
    "SAFETY_STOP",
    "ON_SITE_TROUBLESHOOT",
    "CATCH_REPORT",
    "PLAN_TRIP",
    "TACKLE_QA",
    "KNOWLEDGE_QA",
    "PERSONAL_INSIGHT",
    "UNKNOWN",
]


class IntentResult(BaseModel):
    """意图识别结果：主意图 + 次意图 + 置信度 + 证据。"""

    primary_intent: PrimaryIntent = "UNKNOWN"
    secondary_intents: list[str] = Field(default_factory=list)
    confidence: Literal["high", "mid", "low"] = "mid"
    evidence: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None
    # 前端可回传已解析的上下文（用于纠正/补充）
    context: Optional[dict[str, Any]] = None


class FishingContext(BaseModel):
    """对话槽位（对齐 PRD 10.2 + V1.2 硬约束）。"""

    location: Optional[str] = None
    lat: Optional[float] = None  # 精确定位纬度（WGS-84）
    lon: Optional[float] = None  # 精确定位经度（WGS-84）
    target_species: Optional[str] = None

    # 用户可用时间（带时区 ISO 8601）
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    time_window: Optional[str] = None  # 原始文本，如"明早"
    time_label: Optional[str] = None  # 解析后的绝对表述，如"明天 05:00–09:00"
    timezone: str = "Asia/Shanghai"

    # 出行范围（结构化）
    travel_radius: Optional[str] = None  # 原始文本，如"40分钟"
    max_travel_minutes: Optional[int] = None
    max_distance_km: Optional[float] = None

    water_type: Optional[str] = None
    tackle: Optional[str] = None
    skill_level: str = "入门"
    constraints: list[str] = Field(default_factory=list)

    # 每个槽位来源：message(本轮) / history(历史) / default(默认)
    slot_sources: dict[str, str] = Field(default_factory=dict)


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
    """方案卡（对应决策卡字段，PRD 12 节 + V1.2 数据质量）。"""

    session_id: Optional[str] = None
    version: int = 1
    location: Optional[str] = None
    time_window: Optional[str] = None
    target_species: Optional[str] = None
    travel_radius: Optional[str] = None
    conclusion: Literal["go", "conditional", "no_go"] = "conditional"
    confidence: Literal["high", "mid", "low"] = "mid"
    score: int = Field(ge=0, le=100)  # 内部条件分数，UI 不再直接展示单点分
    best_window: Optional[str] = None
    backup_window: Optional[str] = None
    factors: list[str] = Field(default_factory=list)
    plan_detail: PlanDetail = Field(default_factory=PlanDetail)
    risks: list[str] = Field(default_factory=list)
    safety: list[str] = Field(default_factory=list)
    data_basis: dict[str, Any] = Field(default_factory=dict)
    history_note: Optional[str] = None

    # V1.2 数据质量与条件档位
    data_completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    condition_band: Literal["good", "fair", "poor"] = "fair"
    condition_score_range: Optional[tuple[int, int]] = None


class ChatDonePayload(BaseModel):
    type: Literal["reply", "plan", "clarify", "error"]
    reply: str = ""
    plan: Optional[PlanData] = None
    missing: list[str] = Field(default_factory=list)


class PlanCreateRequest(PlanData):
    pass


class ValidationIssue(BaseModel):
    """决策后一致性校验问题。"""

    code: str
    severity: Literal["error", "warning"]
    message: str
