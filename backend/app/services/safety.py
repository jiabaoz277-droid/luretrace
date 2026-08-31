"""P0 对话边界。

这里只放必须在调用模型、读取会话模式之前生效的确定性规则，
避免将合规拒答交给模型“自觉”执行。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class BoundaryDecision:
    kind: str
    reply: str


_ILLEGAL_METHODS: dict[str, str] = {
    "电鱼": "电鱼",
    "电捕": "电鱼",
    "电鱼机": "电鱼",
    "电鱼器": "电鱼",
    "毒鱼": "毒鱼",
    "毒鱼药": "毒鱼",
    "炸鱼": "炸鱼",
    "锚鱼": "锚鱼",
    "锚钩": "锚鱼",
}

_LIVE_BAIT = ("泥鳅", "泥鳅党", "活饵", "活鱼", "活虾")
_BANNED_PURCHASE = (
    "禁售渔具",
    "违禁渔具",
    "绝户网",
    "粘网",
    "粘鱼网",
    "电鱼机",
    "电鱼器",
    "毒鱼药",
)

_FISHING_DOMAIN = (
    "路亚", "钓", "鱼", "出钓", "鱼口", "空军", "没口", "跑鱼", "脱钩",
    "挂底", "炸水", "追饵", "蹭饵", "竿", "轮", "线", "钩", "拟饵", "亮片",
    "米诺", "vib", "铅笔", "波爬", "雷蛙", "软饵", "水层", "标点", "水域",
    "江", "河", "湖", "库", "溪", "禁渔", "禁钓", "渔具", "天气", "气压",
    "风", "雨", "雷暴", "涨水", "水温", "水位",
    "新手", "入门", "误区", "技巧", "手法", "装备", "战报", "复盘",
    "收藏", "规律", "出发", "定位",
)

_OBVIOUSLY_UNRELATED = (
    "python", "javascript", "java", "写代码", "编程", "爬虫", "数据库",
    "股票", "基金", "虚拟币", "比特币", "财报", "房价", "房贷",
    "写作业", "论文", "翻译", "写文案", "写诗", "写小说", "讲笑话",
    "感冒", "发烧", "吃什么药", "医院", "医生", "法律咨询",
    "明星", "电影", "电视剧", "游戏攻略", "足球", "篮球",
)

_NEGATIVE_EMOTION = (
    "妈的", "妈了个巴子", "他妈的", "操", "草", "滚", "垃圾", "废物",
    "烦死", "气死", "气炸", "崩溃", "破防", "真烦", "太烦", "真无语",
)

_CONTEXTUAL_FOLLOWUPS = (
    "是", "是的", "不是", "对", "对的", "不对", "可以", "不可以", "行", "不行",
    "好", "好的", "继续", "换一个", "不知道", "没有", "有", "确认", "取消",
    "安全吗", "危险吗",
)

_ONSITE_FOLLOWUPS = (
    "浑", "清", "黄", "绿", "浑水", "清水", "急流", "缓流", "静水", "走水", "流水",
    "掉了", "挣脱", "没动静", "没反应", "只跟", "扑食",
)

_REPORT_FOLLOWUPS = (
    "没去", "未出钓", "取消", "上鱼", "中鱼", "钓到", "爆护", "有口", "空军",
    "确认", "写入", "保存", "算了",
)


def _normalise(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).lower().translate(
        str.maketrans({"電": "电", "魚": "鱼", "鰍": "鳅", "藥": "药", "買": "买"})
    )
    # 去掉空白、标点、控制字符，阻止“电-鱼”“泥_鳅”等拆词绕过。
    return "".join(ch for ch in value if unicodedata.category(ch)[0] not in {"P", "Z", "C"})


def compliance_block(text: str) -> BoundaryDecision | None:
    """命中违规捕捞或活饵后立即拒答，不进入其他会话模式。"""
    value = _normalise(text)

    semantic_method = None
    if re.search(r"(?:用|拿|接|开)?电.{0,6}(?:捕|捞|弄|抓|钓)?.{0,3}鱼", value) or re.search(
        r"鱼.{0,4}(?:通电|电击)", value
    ):
        semantic_method = "电鱼"
    elif re.search(r"(?:下|投|撒|放|用).{0,3}(?:药|毒).{0,5}(?:鱼|捕鱼)", value):
        semantic_method = "毒鱼"
    if semantic_method:
        return BoundaryDecision(
            kind="compliance_refusal",
            reply=(
                f"这个不能帮你：{semantic_method}属于违规捕捞，我不提供操作、设备、材料、"
                "购买渠道或规避监管的信息。请改用人工拟饵等合规方式，并以当地法规和现场告示为准。"
            ),
        )

    for keyword, label in _ILLEGAL_METHODS.items():
        if keyword in value:
            return BoundaryDecision(
                kind="compliance_refusal",
                reply=(
                    f"这个不能帮你：{label}属于违规捕捞，我不提供操作、设备、"
                    "材料、购买渠道或规避监管的信息。这类行为会破坏渔业资源，"
                    "并可能承担法律责任。如果你想正常作钓，我可以改为推荐人工拟饵、"
                    "合规钓组和可作钓时段；出发前请以当地禁渔规定与现场告示为准。"
                ),
            )

    if any(keyword in value for keyword in _LIVE_BAIT):
        return BoundaryDecision(
            kind="compliance_refusal",
            reply=(
                "不可以。泥鳅、活鱼、活虾等活饵不属于本路亚助手支持的合规作钓方式，"
                "我不提供用法、钓点或装备建议。请改用亮片、米诺、VIB 或软饵等人工拟饵，"
                "并遵守当地禁渔期、禁钓区及现场告示。"
            ),
        )

    if any(keyword in value for keyword in _BANNED_PURCHASE) or (
        any(k in value for k in ("买", "购买", "哪买", "链接", "渠道"))
        and any(k in value for k in ("禁售", "违禁", "非法渔具"))
    ):
        return BoundaryDecision(
            kind="compliance_refusal",
            reply=(
                "我不能帮你查找、购买或使用禁售、违禁渔具。请选择当地规定允许的"
                "路亚竿、单钩或无倒刺钩与人工拟饵，购买前核对当地禁渔规定和水域告示。"
            ),
        )
    return None


def is_negative(text: str) -> bool:
    value = _normalise(text)
    return any(keyword in value for keyword in _NEGATIVE_EMOTION)


def emotion_preamble() -> str:
    return "先别急，连续没口或现场不顺确实容易让人烦躁。咱们先把问题拆开处理。\n\n"


def is_out_of_scope(
    text: str,
    *,
    primary_intent: str,
    has_active_fishing_context: bool,
    has_message_fishing_slots: bool,
    active_mode: str | None,
) -> bool:
    """无路亚信号的输入不得复用旧会话槽位生成新方案。"""
    value = _normalise(text)
    if any(keyword in value for keyword in _OBVIOUSLY_UNRELATED):
        return True
    if any(keyword in value for keyword in _FISHING_DOMAIN):
        return False
    if has_message_fishing_slots:
        return False

    # 仅允许实际会话流程中的有限短回答，不因为“存在旧上下文”就放行任意闲聊。
    if has_active_fishing_context and value in _CONTEXTUAL_FOLLOWUPS:
        return False
    if active_mode == "onsite" and any(k in value for k in _ONSITE_FOLLOWUPS):
        return False
    if active_mode == "report":
        if any(k in value for k in _REPORT_FOLLOWUPS):
            return False
        if re.fullmatch(r"\d{1,3}(?:条|尾|斤|两|厘米|公分|cm)?", value):
            return False

    # primary_intent 可能被“哪里/为什么”等通用词误命中，不能单独作为放行依据。
    _ = primary_intent
    return True


def out_of_scope_reply() -> str:
    return (
        "这个问题和路亚作钓无关，我先不展开回答。我可以帮你判断今天值不值得去、"
        "选时段和水域、搭配人工拟饵，或排查没口、跑鱼、挂底等问题。"
    )
