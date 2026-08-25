"""淡水路亚对象鱼知识库（结构化规则，MVP 内置 10 种）。

字段说明：
- water_layer: 目标水层
- lures: 拟饵方案（按优先级排序）
- prime_time: 最活跃时段描述
- spots: 典型标点类型
"""
from __future__ import annotations

SPECIES_KNOWLEDGE: dict[str, dict] = {
    "翘嘴": {
        "water_layer": "中上层",
        "lures": [
            {"type": "亮片", "weight": "7–10g", "color": "银色", "action": "扇形搜索中上层"},
            {"type": "沉水铅笔", "weight": "7–12g", "color": "银白", "action": "压低一层慢收"},
            {"type": "米诺", "weight": "9–13g", "color": "自然色", "action": "抽停"},
        ],
        "prime_time": "清晨低光窗口与傍晚",
        "spots": ["入水口", "背风岸", "明暗交界", "浅滩"],
    },
    "鳜鱼": {
        "water_layer": "底层",
        "lures": [
            {"type": "铅头钩+软饵", "weight": "5–10g", "color": "自然色/荧光", "action": "贴底跳停"},
            {"type": "德州钓组", "weight": "7–14g", "color": "绿/棕", "action": "结构区慢搜"},
            {"type": "倒吊", "weight": "5–10g", "color": "自然色", "action": "定点精磨"},
        ],
        "prime_time": "早晚与阴天、水流变化时段",
        "spots": ["乱石区", "桥墩", "深浅交界", "障碍边缘"],
    },
    "鲈鱼": {
        "water_layer": "中下层",
        "lures": [
            {"type": "德州钓组", "weight": "7–12g", "color": "绿/西瓜", "action": "障碍区抖跳"},
            {"type": "倒吊", "weight": "5–9g", "color": "自然色", "action": "贴底慢拖"},
            {"type": "卷尾软虫", "weight": "5–8g", "color": "黑/绿", "action": "匀速收线"},
        ],
        "prime_time": "清晨与傍晚，阴天全天可钓",
        "spots": ["水草边", "枯木", "码头桩", "岩石结构"],
    },
    "黑鱼": {
        "water_layer": "表层障碍区",
        "lures": [
            {"type": "雷蛙", "weight": "8–15g", "color": "深色", "action": "障碍上拖停"},
            {"type": "波爬", "weight": "7–10g", "color": "亮色", "action": "水面抽停"},
        ],
        "prime_time": "气温高、中午前后",
        "spots": ["水草区", "荷叶边", "芦苇丛", "浮萍区"],
    },
    "马口": {
        "water_layer": "中上层",
        "lures": [
            {"type": "小亮片", "weight": "2–4g", "color": "金/银", "action": "溪流顺流搜"},
            {"type": "小飞蝇钩", "weight": "微物", "color": "自然色", "action": "漂落"},
        ],
        "prime_time": "全天，清晨更佳",
        "spots": ["溪流浅滩", "流水缓区", "入水口"],
    },
    "白条": {
        "water_layer": "上层",
        "lures": [
            {"type": "小亮片", "weight": "1–3g", "color": "银", "action": "快速收线"},
            {"type": "小波爬", "weight": "2–4g", "color": "亮色", "action": "水面小抽"},
        ],
        "prime_time": "清晨与傍晚",
        "spots": ["水面开阔区", "下风处", "入水口"],
    },
    "红尾": {
        "water_layer": "中上层",
        "lures": [
            {"type": "亮片", "weight": "7–12g", "color": "银", "action": "中上层快搜"},
            {"type": "米诺", "weight": "9–14g", "color": "自然色", "action": "抽停"},
        ],
        "prime_time": "清晨低光与傍晚",
        "spots": ["入水口", "急流边", "深浅交界"],
    },
    "青稍": {
        "water_layer": "中上层",
        "lures": [
            {"type": "小亮片", "weight": "3–7g", "color": "银", "action": "匀速收线"},
            {"type": "小铅笔", "weight": "5–8g", "color": "自然色", "action": "走之字"},
        ],
        "prime_time": "清晨与傍晚",
        "spots": ["近岸浅滩", "明暗交界", "下风处"],
    },
    "军鱼": {
        "water_layer": "中下层流水",
        "lures": [
            {"type": "亮片", "weight": "7–12g", "color": "金", "action": "急流逆流搜"},
            {"type": "VIB", "weight": "10–15g", "color": "自然色", "action": "快收贴底"},
        ],
        "prime_time": "清晨与傍晚，急流更佳",
        "spots": ["急流", "回水湾", "乱石滩"],
    },
    "罗非": {
        "water_layer": "全层",
        "lures": [
            {"type": "小软饵", "weight": "3–6g", "color": "红/荧光", "action": "慢跳底"},
            {"type": "小亮片", "weight": "2–5g", "color": "金", "action": "缓收"},
        ],
        "prime_time": "气温稳定时段",
        "spots": ["浅滩", "水草边", "避风湾"],
    },
}

# 目标鱼别名 → 规范名
SPECIES_ALIASES = {
    "翘嘴": "翘嘴",
    "翘嘴鱼": "翘嘴",
    "白丝": "翘嘴",
    "撅嘴": "翘嘴",
    "鳜鱼": "鳜鱼",
    "桂鱼": "鳜鱼",
    "桂花鱼": "鳜鱼",
    "鲈鱼": "鲈鱼",
    "大嘴鲈": "鲈鱼",
    "黑鱼": "黑鱼",
    "乌鱼": "黑鱼",
    "乌鳢": "黑鱼",
    "马口": "马口",
    "白条": "白条",
    "餐条": "白条",
    "红尾": "红尾",
    "红尾梢": "红尾",
    "青稍": "青稍",
    "青梢": "青稍",
    "军鱼": "军鱼",
    "倒刺鲃": "军鱼",
    "罗非": "罗非",
    "罗非鱼": "罗非",
    "非洲鲫": "罗非",
}


def normalize_species(name: str) -> str | None:
    return SPECIES_ALIASES.get(name.strip())


def get_species(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = normalize_species(name)
    if normalized:
        return SPECIES_KNOWLEDGE.get(normalized)
    return None
