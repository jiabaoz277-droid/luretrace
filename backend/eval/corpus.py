"""槽位抽取验收语料（100 条）。

字段：
- text: 输入
- location: 期望地点（None 表示该条不含地点，正确行为是抽到空）
- species: 期望目标鱼（None 表示不含）
- time_resolved: True=含时间且应解析为绝对时间；False=不含时间（应抽到空）

用途：评测 FR-01「三个关键槽位完全正确率 ≥90%（50 条标准语料）」。
"""
from __future__ import annotations

CITIES = ["杭州", "上海", "苏州", "武汉", "长沙", "成都", "南京", "宁波", "嘉兴", "湖州"]
TIMES = ["明早", "明天早上", "后天", "周末", "今天傍晚", "周六早上", "明晚", "今晚"]
SPECIES = ["翘嘴", "鳜鱼", "鲈鱼", "黑鱼", "马口"]
RADII = ["两小时", "一小时", "40公里", "30分钟"]

_TEMPLATES = [
    "{t}{city}周边{r}，想打{sp}",
    "{t}去{city}附近路亚，目标{sp}，{r}内",
    "{city}{r}范围内，{t}打{sp}",
]


def _standard() -> list[dict]:
    cases = []
    for i in range(50):
        city = CITIES[i % len(CITIES)]
        t = TIMES[i % len(TIMES)]
        sp = SPECIES[i % len(SPECIES)]
        r = RADII[i % len(RADII)]
        tmpl = _TEMPLATES[i % len(_TEMPLATES)]
        cases.append(
            {
                "text": tmpl.format(t=t, city=city, sp=sp, r=r),
                "location": city,
                "species": sp,
                "time_resolved": True,
            }
        )
    return cases


def _h(cases: list[tuple]) -> list[dict]:
    return [
        {"text": t, "location": loc, "species": sp, "time_resolved": tr}
        for t, loc, sp, tr in cases
    ]


STANDARD_CASES = _standard()

HARD_CASES = _h(
    [
        # A. 相对时间（8）
        ("下班后想去路亚", None, None, True),
        ("后天一早杭州打翘嘴", "杭州", "翘嘴", True),
        ("周五晚上千岛湖打鳜鱼", "千岛湖", "鳜鱼", True),
        ("夜里去打黑鱼", None, "黑鱼", True),
        ("明天下午去苏州", "苏州", None, True),
        ("周末一早武汉打马口", "武汉", "马口", True),
        ("今晚上海附近打鲈鱼", "上海", "鲈鱼", True),
        ("今天中午长沙打白条", "长沙", "白条", True),
        # B. 目标鱼别名（8）
        ("想打桂鱼", None, "鳜鱼", False),
        ("白丝好钓吗", None, "翘嘴", False),
        ("打乌鱼用什么饵", None, "黑鱼", False),
        ("大嘴鲈在哪里钓", None, "鲈鱼", False),
        ("非洲鲫能路亚吗", None, "罗非", False),
        ("青梢怎么打", None, "青稍", False),
        ("红尾什么时候开口", None, "红尾", False),
        ("想钓军鱼", None, "军鱼", False),
        # C. 水域/地点（6）
        ("富春江今天能去吗", "富春江", None, True),
        ("钱塘江口打翘嘴", "钱塘江", "翘嘴", False),
        ("千岛湖水库打鳜鱼", "千岛湖", "鳜鱼", False),
        ("太湖边打黑鱼", "太湖", "黑鱼", False),
        ("杭州西湖能钓吗", "西湖", None, False),
        ("苕溪打马口", "苕溪", "马口", False),
        # D. 装备/约束（6）
        ("我只有ML竿和7g亮片，明早杭州打翘嘴", "杭州", "翘嘴", True),
        ("不夜钓，周六白天上海附近打鲈鱼", "上海", "鲈鱼", True),
        ("带孩子不想跑太远，杭州周边打黑鱼", "杭州", "黑鱼", False),
        ("微物竿能打马口吗，苏州", "苏州", "马口", False),
        ("只有一个小时的功夫，南京打翘嘴", "南京", "翘嘴", False),
        ("不涉水，宁波打鳜鱼", "宁波", "鳜鱼", False),
        # E. 缺失信息（6）
        ("明早想去路亚", None, None, True),
        ("杭州", "杭州", None, False),
        ("想打鳜鱼", None, "鳜鱼", False),
        ("今天能钓吗", None, None, True),
        ("附近有什么好地方", None, None, False),
        ("周末去哪", None, None, True),
        # F. 距离表达（5）
        ("一小时车程内去哪打翘嘴", None, "翘嘴", False),
        ("50公里内打黑鱼", None, "黑鱼", False),
        ("半小时能到的地方打马口", None, "马口", False),
        ("一个半小时车程打鲈鱼", None, "鲈鱼", False),
        ("20分钟以内打白条", None, "白条", False),
        # G. 多意图/复合（5）
        ("周六早上杭州附近打翘嘴，只有两小时", "杭州", "翘嘴", True),
        ("明天想去苏州打鳜鱼顺便带朋友", "苏州", "鳜鱼", True),
        ("后天去嘉兴，钓鲈鱼，不走高速", "嘉兴", "鲈鱼", True),
        ("武汉周边30公里，明早打翘嘴", "武汉", "翘嘴", True),
        ("成都附近，周末下午，目标黑鱼", "成都", "黑鱼", True),
        # H. 纠正/变更（4）
        ("改成下午", None, None, True),
        ("不去杭州了改苏州", "苏州", None, False),
        ("不是翘嘴，是鳜鱼", None, "鳜鱼", False),
        ("距离改成一小时", None, None, False),
        # I. 确认不误报时间（2）
        ("翘嘴用什么饵好", None, "翘嘴", False),
        ("路亚竿怎么选", None, None, False),
    ]
)
