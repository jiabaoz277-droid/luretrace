"""鱼种识别与知识库覆盖测试。"""
from app.services.knowledge import get_species, normalize_species, recommend_species, region_for_province


def test_normalize_new_species():
    cases = {
        "草鱼": "草鱼", "鲩鱼": "草鱼",
        "鲫鱼": "鲫鱼", "鲫瓜子": "鲫鱼",
        "鲤鱼": "鲤鱼", "鲤拐子": "鲤鱼",
        "鲶鱼": "鲶鱼", "塘鲺": "鲶鱼",
        "黄辣丁": "黄颡鱼", "昂刺鱼": "黄颡鱼",
        "鳡鱼": "鳡鱼", "水老虎": "鳡鱼",
        "虹鳟": "虹鳟", "鳟鱼": "虹鳟",
        "鳊鱼": "鳊鱼", "武昌鱼": "鳊鱼",
        "太阳鱼": "太阳鱼", "蓝鳃": "太阳鱼",
        "白鲳": "白鲳", "鲳鱼": "白鲳",
        "赤眼鳟": "赤眼鳟", "红眼": "赤眼鳟",
        "鲮鱼": "鲮鱼", "土鲮": "鲮鱼",
        "鲢鳙": "鲢鳙", "胖头鱼": "鲢鳙", "花鲢": "鲢鳙",
        "狗鱼": "狗鱼",
    }
    for alias, expected in cases.items():
        assert normalize_species(alias) == expected, f"{alias} 应识别为 {expected}"


def test_knowledge_covers_all():
    for alias, species in [
        ("草鱼", "草鱼"), ("鲫鱼", "鲫鱼"), ("鲤鱼", "鲤鱼"),
        ("鲶鱼", "鲶鱼"), ("黄颡鱼", "黄颡鱼"), ("鳡鱼", "鳡鱼"),
        ("虹鳟", "虹鳟"), ("鳊鱼", "鳊鱼"), ("太阳鱼", "太阳鱼"),
        ("鲢鳙", "鲢鳙"), ("狗鱼", "狗鱼"),
    ]:
        k = get_species(species)
        assert k is not None, f"{species} 应有知识"
        assert k["lures"], f"{species} 应有拟饵方案"
        assert k["water_layer"] and k["prime_time"] and k["spots"]


def test_original_species_still_work():
    for species in ["翘嘴", "鳜鱼", "鲈鱼", "黑鱼", "马口", "白条", "红尾", "青稍", "军鱼", "罗非"]:
        assert get_species(species) is not None


def test_region_for_province():
    assert region_for_province("湖北") == "南方"
    assert region_for_province("黑龙江") == "北方"
    assert region_for_province(None) == "全国"


def test_recommend_species_by_region():
    # 南方应含南方特色鱼，不含北方冷水鱼
    south = recommend_species(8, "南方")
    assert ("罗非" in south) or ("鳡鱼" in south)
    assert "狗鱼" not in south and "虹鳟" not in south
    # 北方应含北方冷水鱼，不含南方热带鱼
    north = recommend_species(8, "北方")
    assert ("狗鱼" in north) or ("虹鳟" in north)
    assert "罗非" not in north and "鲮鱼" not in north
