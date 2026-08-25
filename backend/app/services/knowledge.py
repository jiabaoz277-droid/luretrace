"""淡水鱼种知识库（结构化规则，覆盖常见路亚对象鱼与常见淡水鱼）。

字段说明：
- water_layer: 目标水层
- lures: 拟饵方案（按优先级排序）
- prime_time: 最活跃时段描述
- spots: 典型标点类型
"""
from __future__ import annotations

SPECIES_KNOWLEDGE: dict[str, dict] = {
    # ===== 路亚主要对象鱼 =====
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
    # ===== 路亚对象鱼（补充） =====
    "鳡鱼": {
        "water_layer": "中上层",
        "lures": [
            {"type": "大亮片", "weight": "10–20g", "color": "银", "action": "快速搜索"},
            {"type": "水面铅笔", "weight": "10–15g", "color": "自然色", "action": "水面快抽"},
            {"type": "米诺", "weight": "12–18g", "color": "银白", "action": "抽停"},
        ],
        "prime_time": "清晨与傍晚，追小鱼时更活跃",
        "spots": ["入水口", "急流", "深浅交界", "水面炸水处"],
    },
    "狗鱼": {
        "water_layer": "中上层",
        "lures": [
            {"type": "大亮片", "weight": "10–18g", "color": "银/铜", "action": "匀速快收"},
            {"type": "米诺", "weight": "10–15g", "color": "自然色", "action": "抽停"},
        ],
        "prime_time": "清晨与傍晚",
        "spots": ["水草边缘", "浅滩", "入水口"],
    },
    "虹鳟": {
        "water_layer": "中上层",
        "lures": [
            {"type": "小亮片", "weight": "2–5g", "color": "金/银", "action": "匀速收线"},
            {"type": "飞蝇", "weight": "微物", "color": "自然色", "action": "漂落"},
        ],
        "prime_time": "清晨与傍晚，冷水更佳",
        "spots": ["流水浅滩", "深潭", "入水口"],
    },
    "太阳鱼": {
        "water_layer": "中下层",
        "lures": [
            {"type": "小软饵", "weight": "2–5g", "color": "自然色", "action": "慢跳底"},
            {"type": "小亮片", "weight": "2–4g", "color": "金", "action": "缓收"},
        ],
        "prime_time": "全天，暖季更佳",
        "spots": ["浅滩", "水草边", "障碍边"],
    },
    "白鲳": {
        "water_layer": "中上层",
        "lures": [
            {"type": "小亮片", "weight": "3–7g", "color": "银", "action": "快速收线"},
            {"type": "小软饵", "weight": "3–5g", "color": "红/荧光", "action": "中上层慢收"},
        ],
        "prime_time": "水温较高时段",
        "spots": ["水面开阔区", "入水口", "下风处"],
    },
    "赤眼鳟": {
        "water_layer": "中上层",
        "lures": [
            {"type": "小亮片", "weight": "3–7g", "color": "金/银", "action": "匀速收线"},
            {"type": "小软饵", "weight": "3–5g", "color": "自然色", "action": "慢收"},
        ],
        "prime_time": "清晨与傍晚",
        "spots": ["流水缓区", "入水口", "浅滩"],
    },
    "鲮鱼": {
        "water_layer": "底层",
        "lures": [
            {"type": "小软饵", "weight": "2–5g", "color": "自然色", "action": "贴底慢拖"},
        ],
        "prime_time": "水温稳定时段",
        "spots": ["缓流区", "沙底", "入水口"],
    },
    "鳊鱼": {
        "water_layer": "中上层",
        "lures": [
            {"type": "小亮片", "weight": "2–5g", "color": "银", "action": "匀速收线"},
            {"type": "微物软饵", "weight": "2–4g", "color": "自然色", "action": "中上层慢收"},
        ],
        "prime_time": "清晨与傍晚",
        "spots": ["水面开阔区", "入水口", "下风处"],
    },
    # ===== 常见淡水鱼（可识别，路亚非首选） =====
    "草鱼": {
        "water_layer": "中下层",
        "lures": [
            {"type": "软饵", "weight": "5–10g", "color": "绿/自然", "action": "贴底慢拖"},
            {"type": "小亮片", "weight": "3–7g", "color": "金", "action": "中下层慢收"},
        ],
        "prime_time": "清晨与傍晚，夏季高温时段",
        "spots": ["水草边", "浅滩", "入水口"],
    },
    "鲤鱼": {
        "water_layer": "底层",
        "lures": [
            {"type": "软饵", "weight": "5–12g", "color": "自然色", "action": "贴底极慢拖"},
            {"type": "小胖", "weight": "5–8g", "color": "自然色", "action": "贴底缓收"},
        ],
        "prime_time": "清晨与傍晚",
        "spots": ["深潭", "缓流区", "障碍边"],
    },
    "鲫鱼": {
        "water_layer": "底层",
        "lures": [
            {"type": "微物软饵", "weight": "1–3g", "color": "自然色", "action": "贴底慢拖"},
        ],
        "prime_time": "清晨与傍晚",
        "spots": ["浅滩", "水草边", "缓流区"],
    },
    "鲶鱼": {
        "water_layer": "底层",
        "lures": [
            {"type": "大软饵", "weight": "10–20g", "color": "深色/荧光", "action": "贴底慢跳"},
            {"type": "VIB", "weight": "10–15g", "color": "自然色", "action": "贴底快收"},
        ],
        "prime_time": "夜间与清晨",
        "spots": ["深潭", "桥墩", "乱石区"],
    },
    "黄颡鱼": {
        "water_layer": "底层",
        "lures": [
            {"type": "小软饵", "weight": "2–5g", "color": "荧光", "action": "贴底慢拖"},
        ],
        "prime_time": "夜间与清晨",
        "spots": ["乱石区", "桥墩", "缓流底"],
    },
    "鲢鳙": {
        "water_layer": "中上层",
        "lures": [
            {"type": "微物亮片/飞蝇", "weight": "微物", "color": "自然色", "action": "滤食性，路亚效率低"},
        ],
        "prime_time": "高温时段浮头",
        "spots": ["水面开阔区", "下风处"],
    },
}

# 季节 → 推荐目标鱼（中国大陆淡水路亚，按月份）
SEASON_SPECIES: dict[tuple[int, ...], list[str]] = {
    (3, 4, 5): ["翘嘴", "鳜鱼", "鲈鱼", "马口"],
    (6, 7, 8): ["翘嘴", "鳜鱼", "鲈鱼", "黑鱼", "白条"],
    (9, 10, 11): ["翘嘴", "鳜鱼", "鲈鱼", "红尾"],
    (12, 1, 2): ["翘嘴", "鳜鱼"],
}


def recommend_species(month: int) -> list[str]:
    """按月份推荐候选目标鱼（最多 3 个）。"""
    for months, species in SEASON_SPECIES.items():
        if month in months:
            return species[:3]
    return ["翘嘴", "鳜鱼", "鲈鱼"]


# 目标鱼别名 → 规范名
SPECIES_ALIASES = {
    "翘嘴": "翘嘴", "翘嘴鱼": "翘嘴", "白丝": "翘嘴", "撅嘴": "翘嘴",
    "鳜鱼": "鳜鱼", "桂鱼": "鳜鱼", "桂花鱼": "鳜鱼",
    "鲈鱼": "鲈鱼", "大嘴鲈": "鲈鱼",
    "黑鱼": "黑鱼", "乌鱼": "黑鱼", "乌鳢": "黑鱼", "生鱼": "黑鱼",
    "马口": "马口",
    "白条": "白条", "餐条": "白条", "蓝刀": "白条",
    "红尾": "红尾", "红尾梢": "红尾",
    "青稍": "青稍", "青梢": "青稍",
    "军鱼": "军鱼", "倒刺鲃": "军鱼",
    "罗非": "罗非", "罗非鱼": "罗非", "非洲鲫": "罗非",
    # 补充对象鱼
    "鳡鱼": "鳡鱼", "鳡": "鳡鱼", "水老虎": "鳡鱼", "黄钻": "鳡鱼", "竿鱼": "鳡鱼",
    "狗鱼": "狗鱼", "白斑狗鱼": "狗鱼",
    "虹鳟": "虹鳟", "虹鳟鱼": "虹鳟", "鳟鱼": "虹鳟", "三文鳟": "虹鳟",
    "太阳鱼": "太阳鱼", "蓝鳃太阳鱼": "太阳鱼", "蓝鳃": "太阳鱼", "太阳鲈": "太阳鱼",
    "白鲳": "白鲳", "淡水白鲳": "白鲳", "鲳鱼": "白鲳",
    "赤眼鳟": "赤眼鳟", "红眼": "赤眼鳟", "红眼鳟": "赤眼鳟", "赤眼": "赤眼鳟",
    "鲮鱼": "鲮鱼", "土鲮": "鲮鱼", "麦鲮": "鲮鱼", "泰鲮": "鲮鱼",
    "鳊鱼": "鳊鱼", "武昌鱼": "鳊鱼", "三角鲂": "鳊鱼", "鲂鱼": "鳊鱼", "团头鲂": "鳊鱼",
    # 常见淡水鱼
    "草鱼": "草鱼", "草棒": "草鱼", "鲩鱼": "草鱼", "草鲩": "草鱼",
    "鲤鱼": "鲤鱼", "鲤拐子": "鲤鱼", "红鱼": "鲤鱼", "鲤子": "鲤鱼",
    "鲫鱼": "鲫鱼", "鲫瓜子": "鲫鱼", "土鲫": "鲫鱼", "鲫壳": "鲫鱼",
    "鲶鱼": "鲶鱼", "鲇鱼": "鲶鱼", "塘鲺": "鲶鱼", "胡子鲶": "鲶鱼",
    "黄颡鱼": "黄颡鱼", "黄辣丁": "黄颡鱼", "昂刺鱼": "黄颡鱼", "黄骨鱼": "黄颡鱼", "嘎牙子": "黄颡鱼",
    "鲢鳙": "鲢鳙", "白鲢": "鲢鳙", "花鲢": "鲢鳙", "胖头鱼": "鲢鳙", "鳙鱼": "鲢鳙",
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
