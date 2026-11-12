"""Built-in starting recipe for random style datasets.

Its vocabulary and rough weights come from the retired fixed style library
(apps/web/src/dataset-prompts.ts, removed with this feature): content-only Danbooru tags,
no artist/medium/quality tags. Ids are fixed so recipes created from the template share
draw ids in review filters. Single adult person or no-human only; there are no child
options, so the recipe needs no child-safety guards.
"""

from typing import Any

from .recipe_engine import DatasetRecipe

FEMALE = {"state": "gender", "in": ["female"]}
OUTDOOR = {"state": "place", "in": ["outdoor"]}
NO_OUTFIT = {"not": {"partition_drawn": "outfit"}}
LONG_ENOUGH = {"all": [FEMALE, {"not": {"state": "hair", "in": ["short"]}}]}


def _o(id: str, label: str, tags: str, weight: float = 1, **extra: Any) -> dict:
    return {"id": id, "label": label, "tags": tags, "weight": weight, **extra}


def _none(label: str, weight: float, **extra: Any) -> dict:
    return {"id": "none", "none": True, "label": label, "weight": weight, **extra}


def _p(id: str, label: str, options: list[dict], **extra: Any) -> dict:
    return {"id": id, "label": label, "options": options, **extra}


def _hands(n: int) -> dict:
    return {"consume": {"hands": n}}


COLORS = [
    ("white", "white", "白色", 10), ("black", "black", "黑色", 10),
    ("navy", "navy blue", "藏青色", 5), ("blue", "blue", "蓝色", 6),
    ("light-blue", "light blue", "浅蓝色", 4), ("red", "red", "红色", 6),
    ("pink", "pink", "粉色", 5), ("green", "green", "绿色", 4),
    ("yellow", "yellow", "黄色", 4), ("purple", "purple", "紫色", 3),
    ("grey", "grey", "灰色", 5), ("brown", "brown", "棕色", 4),
    ("beige", "beige", "米色", 4),
]

PARTITIONS = [
    _p("subject", "主体", [
        _o("woman", "成年女性", "1girl, solo", 85,
           effects={"set": {"gender": "female", "age": "adult"}}),
        _o("man", "成年男性", "1boy, solo", 3,
           effects={"set": {"gender": "male", "age": "adult"}}),
        _o("no-human", "无人物", "no humans, scenery", 12,
           effects={"hide": ["person"]}, size="landscape"),
    ], quota=True),
    _p("framing", "景别", [
        _o("close-up", "脸部特写", "close-up, face focus", 12,
           effects={"hide": ["upper", "lower", "hands"]}),
        _o("portrait", "肖像", "portrait", 14, effects={"hide": ["lower"]}),
        _o("upper-body", "上半身", "upper body", 26, effects={"hide": ["lower"]}),
        _o("cowboy-shot", "七分身", "cowboy shot", 10, effects={"hide": ["feet"]}),
        _o("full-body", "全身", "full body", 28, size="portrait"),
        _o("wide-shot", "远景", "wide shot", 10, effects={"hide": ["eyes"]}, size="landscape"),
    ], needs=["person"]),
    _p("angle", "视角", [
        _none("平视", 20),
        _o("from-side", "侧面", "from side", 4),
        _o("three-quarter", "四分之三侧", "three-quarter view", 3),
        _o("from-below", "仰视", "from below", 5),
        _o("from-above", "俯视", "from above", 5),
        _o("dutch-angle", "倾斜构图", "dutch angle", 3),
        _o("from-behind", "背面", "from behind", 3, effects={"hide": ["face"]}),
    ], needs=["person"]),
    _p("pose", "整体姿势", [
        _o("standing", "站立", "standing", 18, effects={"set": {"pose": "standing"}}),
        _o("sitting", "坐", "sitting", 18, effects={"set": {"pose": "sitting"}}),
        _o("walking", "行走", "walking", 8, effects={"set": {"pose": "walking"}}),
        _o("running", "奔跑", "running", 3, effects={"set": {"pose": "running"}}),
        _o("lying", "躺", "lying, on back", 3, effects={"set": {"pose": "lying"}},
           size="landscape"),
        _o("kneeling", "跪", "kneeling", 2, effects={"set": {"pose": "kneeling"}}),
        _o("squatting", "蹲", "squatting", 2, effects={"set": {"pose": "squatting"}}),
        _o("jumping", "跳跃", "jumping, midair", 2, effects={"set": {"pose": "jumping"}}),
    ], needs=["lower"]),
    _p("hair-length", "发长", [
        _o("short", "短发", "short hair", 30, effects={"set": {"hair": "short"}}),
        _o("medium", "中发", "medium hair", 10, effects={"set": {"hair": "medium"}}),
        _o("long", "长发", "long hair", 50, effects={"set": {"hair": "long"}}),
        _o("very-long", "超长发", "very long hair", 10, effects={"set": {"hair": "long"}}),
    ], needs=["person"]),
    _p("hairstyle", "发型", [
        _none("披发", 30),
        _o("ponytail", "马尾", "ponytail", 12),
        _o("twintails", "双马尾", "twintails", 7,
           when=LONG_ENOUGH),
        _o("side-ponytail", "侧马尾", "side ponytail", 3, when=FEMALE),
        _o("braid", "辫子", "braid", 5, when=LONG_ENOUGH),
        _o("twin-braids", "双辫", "twin braids", 2,
           when=LONG_ENOUGH),
        _o("hair-bun", "发髻", "hair bun", 6),
        _o("bob-cut", "波波头", "bob cut", 5, when={"state": "hair", "in": ["short"]}),
        _o("hime-cut", "姬发式", "hime cut", 3,
           when={"all": [FEMALE, {"state": "hair", "in": ["long"]}]}),
        _o("wavy", "波浪卷发", "wavy hair", 4),
        _o("messy", "凌乱头发", "messy hair", 2),
    ], needs=["person"]),
    _p("bangs", "刘海", [
        _none("不写刘海", 45),
        _o("parted", "中分", "parted bangs", 25),
        _o("blunt", "齐刘海", "blunt bangs", 15),
        _o("swept", "斜刘海", "swept bangs", 8),
        _o("between-eyes", "眼间刘海", "hair between eyes", 4),
        _o("forehead", "露额头", "forehead, hair pulled back", 5),
        _o("over-one-eye", "遮单眼", "hair over one eye", 3),
    ], needs=["face"]),
    _p("hair-color", "发色", [
        _o("black", "黑发", "black hair", 22), _o("brown", "棕发", "brown hair", 13),
        _o("light-brown", "浅棕发", "light brown hair", 4),
        _o("blonde", "金发", "blonde hair", 14), _o("silver", "银发", "silver hair", 9),
        _o("white", "白发", "white hair", 6), _o("red", "红发", "red hair", 4),
        _o("pink", "粉发", "pink hair", 5), _o("blue", "蓝发", "blue hair", 6),
        _o("orange", "橙发", "orange hair", 4), _o("purple", "紫发", "purple hair", 3),
    ], needs=["person"]),
    _p("expression", "表情", [
        _o("smile", "微笑", "smile", 22), _o("light-smile", "浅笑", "light smile", 10),
        _o("laughing", "大笑", "laughing, open mouth", 5),
        _o("closed-eyes", "闭眼微笑", "closed eyes, smile", 6,
           effects={"hide": ["eyes"], "remove_partitions": ["eye-color"]}),
        _o("serious", "严肃", "serious", 6), _o("calm", "平静", "calm", 4),
        _o("sad", "悲伤", "sad", 3), _o("crying", "哭泣", "crying, tears", 2),
        _o("blush", "脸红", "blush", 3), _o("pout", "噘嘴", "pout", 2),
        _o("surprised", "惊讶", "surprised, open mouth", 3), _o("smirk", "得意笑", "smirk", 4),
        _o("expressionless", "面无表情", "expressionless", 4),
        _o("determined", "坚定", "determined", 3),
        _o("wink", "眨眼", "wink", 2), _o("sleepy", "困倦", "sleepy, half-closed eyes", 2),
    ], needs=["face"]),
    _p("eye-color", "瞳色", [
        _o("blue", "蓝瞳", "blue eyes", 24), _o("green", "绿瞳", "green eyes", 16),
        _o("brown", "棕瞳", "brown eyes", 15), _o("red", "红瞳", "red eyes", 11),
        _o("yellow", "黄瞳", "yellow eyes", 11), _o("purple", "紫瞳", "purple eyes", 8),
        _o("grey", "灰瞳", "grey eyes", 4), _o("amber", "琥珀瞳", "amber eyes", 3),
    ], needs=["eyes"]),
    _p("gaze", "视线", [
        _o("viewer", "看镜头", "looking at viewer", 30),
        _o("away", "看别处", "looking away", 6),
        _o("up", "向上看", "looking up", 6), _o("down", "向下看", "looking down", 4),
        _o("back", "回头看", "looking back", 3),
        _none("不写视线", 15),
    ], needs=["eyes"]),
    _p("outfit", "套装", [
        _none("不穿套装", 70),
        _o("school-uniform", "水手服校服", "school uniform, {color} serafuku", 6, when=FEMALE,
           slots={"color": {"only": ["navy", "white", "black"]}},
           effects={"consume": {"top": 1},
                    "allow_options": {"bottom": ["pleated-skirt"]}}),
        _o("maid", "女仆装", "maid, black dress, white apron", 3, when=FEMALE,
           effects={"consume": {"top": 1, "bottom": 1}}),
        _o("kimono", "和服", "{color} kimono", 4, when=FEMALE,
           slots={"color": {"weight_mods": {"red": 2}}},
           effects={"consume": {"top": 1, "bottom": 1}, "remove_partitions": ["legwear"],
                    "allow_options": {"shoes": ["geta", "none"]}}),
        _o("china-dress", "旗袍", "{color} china dress", 2, when=FEMALE,
           slots={"color": {"exclude": ["green", "beige", "grey"]}},
           effects={"consume": {"top": 1, "bottom": 1}}),
        _o("sundress", "吊带裙", "{color} sundress", 5, when=FEMALE,
           slots={"color": {"only": ["white", "yellow", "light-blue", "pink"]}},
           effects={"consume": {"top": 1, "bottom": 1}}),
        _o("dress", "连衣裙", "{color} dress", 8, when=FEMALE,
           effects={"consume": {"top": 1, "bottom": 1}}),
    ], needs=["upper"], when=FEMALE),
    _p("top", "上衣", [
        _o("t-shirt", "T恤", "{color} t-shirt", 8, slots={"color": {"set_state": "top-color"}},
           effects={"consume": {"top": 1}}),
        _o("shirt", "衬衫", "{color} collared shirt", 6,
           slots={"color": {"set_state": "top-color"}}, effects={"consume": {"top": 1}}),
        _o("blouse", "女式衬衫", "{color} blouse", 8, when=FEMALE,
           slots={"color": {"set_state": "top-color"}}, effects={"consume": {"top": 1}}),
        _o("sweater", "毛衣", "{color} sweater", 7, slots={"color": {"set_state": "top-color"}},
           effects={"consume": {"top": 1}}),
        _o("hoodie", "连帽衫", "{color} hoodie", 4, slots={"color": {"set_state": "top-color"}},
           effects={"consume": {"top": 1}}),
        _o("turtleneck", "高领衫", "{color} turtleneck", 3,
           slots={"color": {"set_state": "top-color"}}, effects={"consume": {"top": 1}}),
        _none("不写上衣", 1),
    ], needs=["upper"], when=NO_OUTFIT),
    _p("outerwear", "外套", [
        _none("无外套", 14),
        _o("jacket", "敞开夹克", "open jacket, {color} jacket", 3,
           slots={"color": {"exclude_state": "top-color"}}),
        _o("coat", "敞开大衣", "open coat, {color} coat", 3,
           slots={"color": {"exclude_state": "top-color",
                            "only": ["black", "beige", "brown", "navy", "grey"]}}),
        _o("cardigan", "敞开开衫", "open cardigan, {color} cardigan", 2,
           slots={"color": {"exclude_state": "top-color"}}),
    ], needs=["upper"], when={"partition_drawn": "top"}),
    _p("bottom", "下装", [
        _o("pleated-skirt", "百褶裙", "{color} pleated skirt", 6, when=FEMALE,
           slots={"color": {"exclude_state": "top-color"}}, effects={"consume": {"bottom": 1}}),
        _o("skirt", "裙子", "{color} skirt", 8, when=FEMALE,
           slots={"color": {"exclude_state": "top-color"}}, effects={"consume": {"bottom": 1}}),
        _o("shorts", "短裤", "{color} shorts", 5,
           slots={"color": {"exclude_state": "top-color"}}, effects={"consume": {"bottom": 1}}),
        _o("jeans", "牛仔裤", "blue jeans", 6, effects={"consume": {"bottom": 1}}),
        _o("pants", "长裤", "{color} pants", 5,
           slots={"color": {"exclude_state": "top-color", "only": ["black", "grey", "beige",
                                                                    "brown", "navy", "white"]}},
           effects={"consume": {"bottom": 1}}),
    ], needs=["lower"], when={"not": {"any": [
        {"chosen": "outfit.maid"}, {"chosen": "outfit.kimono"}, {"chosen": "outfit.china-dress"},
        {"chosen": "outfit.sundress"}, {"chosen": "outfit.dress"}]}}),
    _p("legwear", "袜子", [
        _none("不写袜子", 20),
        _o("white-socks", "白袜", "white socks", 3),
        _o("black-pantyhose", "黑丝裤袜", "black pantyhose", 2, when=FEMALE),
        _o("thighhighs", "过膝袜", "{color} thighhighs", 2, when=FEMALE,
           slots={"color": {"only": ["white", "black"]}}),
    ], needs=["lower"]),
    _p("shoes", "鞋子", [
        _o("brown-boots", "棕色靴子", "brown boots", 18),
        _o("black-boots", "黑色靴子", "black boots", 9),
        _o("sneakers", "运动鞋", "{color} sneakers", 13,
           slots={"color": {"only": ["white", "black", "red"]}}),
        _o("loafers", "乐福鞋", "brown loafers", 6),
        _o("sandals", "凉鞋", "{color} sandals", 5, slots={"color": {"only": ["white", "brown"]}}),
        _o("high-heels", "高跟鞋", "{color} high heels", 3, when=FEMALE,
           slots={"color": {"only": ["black", "white", "red"]}}),
        _o("geta", "木屐", "geta", 4, when={"chosen": "outfit.kimono"}),
        _none("不写鞋子（赤脚）", 6),
    ], needs=["feet"]),
    _p("hands", "手部动作", [
        _none("不写手部", 10),
        _o("arms-up", "双臂举起", "arms up", 2, effects=_hands(2)),
        _o("arms-crossed", "抱臂", "arms crossed", 2, effects=_hands(2)),
        _o("hands-on-hips", "双手叉腰", "hands on own hips", 2, effects=_hands(2)),
        _o("hands-together", "双手合拢", "own hands together", 2, effects=_hands(2)),
        _o("holding-sword", "双手持剑", "holding sword", 2, effects=_hands(2)),
        _o("waving", "挥手", "waving", 3, effects=_hands(1)),
        _o("peace-sign", "比耶", "peace sign", 3, effects=_hands(1), needs=["face"]),
        _o("holding-cup", "拿杯子", "holding cup", 3, effects=_hands(1)),
        _o("holding-book", "拿书", "holding book", 3, effects=_hands(1)),
        _o("holding-phone", "拿手机", "holding phone", 2, effects=_hands(1)),
        _o("holding-umbrella", "撑伞", "holding umbrella", 2, effects=_hands(1)),
        _o("hand-on-cheek", "手托脸颊", "hand on own cheek", 2, effects=_hands(1),
           needs=["face"]),
        _o("hand-on-chest", "手放胸前", "hand on own chest", 2, effects=_hands(1)),
        _o("reaching", "伸手向镜头", "reaching towards viewer", 1, effects=_hands(1)),
    ], needs=["hands"], mode="fill", max_draws=2),
    _p("head", "头部动作", [
        _none("不写头部动作", 12),
        _o("head-tilt", "歪头", "head tilt", 2),
    ], needs=["face"]),
    _p("accessory", "饰品", [
        _none("无饰品", 12),
        _o("hair-ribbon", "发带", "{color} hair ribbon", 2,
           slots={"color": {"only": ["red", "white", "black", "blue", "pink"]}}),
        _o("hairclip", "发夹", "{color} hairclip", 2),
        _o("earrings", "耳环", "earrings", 2, needs=["face"]),
        _o("glasses", "眼镜", "glasses", 2, needs=["eyes"]),
        _o("choker", "颈圈", "black choker", 1),
        _o("scarf", "围巾", "{color} scarf", 2, needs=["upper"],
           slots={"color": {"only": ["red", "white", "grey", "beige"]}}),
        _o("necklace", "项链", "necklace", 1, needs=["upper"]),
        _o("beret", "贝雷帽", "{color} beret", 1, slots={"color": {"only": ["red", "black",
                                                                              "beige"]}}),
        _o("straw-hat", "草帽", "straw hat", 1),
    ], needs=["person"], mode="fill", max_draws=2),
    _p("scene", "场景", [
        _o("classroom", "教室", "classroom, indoors", 4, effects={"set": {"place": "indoor"}}),
        _o("cafe", "咖啡馆", "cafe, indoors", 4, effects={"set": {"place": "indoor"}}),
        _o("bedroom", "卧室", "bedroom, indoors", 4, effects={"set": {"place": "indoor"}}),
        _o("library", "图书馆", "library, indoors", 2, effects={"set": {"place": "indoor"}}),
        _o("kitchen", "厨房", "kitchen, indoors", 2, effects={"set": {"place": "indoor"}}),
        _o("street", "街道", "street, outdoors", 8, effects={"set": {"place": "outdoor"}}),
        _o("park", "公园", "park, outdoors", 4, effects={"set": {"place": "outdoor"}}),
        _o("forest", "森林", "forest, outdoors", 6, effects={"set": {"place": "outdoor"}}),
        _o("beach", "海边", "beach, ocean, outdoors", 3, effects={"set": {"place": "outdoor"}}),
        _o("rooftop", "屋顶", "rooftop, outdoors", 3, effects={"set": {"place": "outdoor"}}),
        _o("shrine", "神社", "shrine, outdoors", 3, effects={"set": {"place": "outdoor"}}),
        _o("field", "花田", "flower field, outdoors", 3, effects={"set": {"place": "outdoor"}}),
        _o("city", "城市", "city, outdoors", 3, effects={"set": {"place": "outdoor"}}),
        _o("simple", "纯色背景", "simple background", 5,
           when={"partition_drawn": "framing"}, effects={"set": {"place": "none"}}),
    ]),
    _p("time", "时间", [
        _o("day", "白天", "day", 30), _o("morning", "清晨", "morning", 4),
        _o("sunset", "黄昏", "sunset", 5), _o("golden-hour", "黄金时刻", "golden hour", 3),
        _o("night", "夜晚", "night", 14, effects={"set": {"time": "night"}}),
    ], when={"not": {"state": "place", "in": ["none"]}}),
    _p("weather", "天气与氛围", [
        _none("不写天气", 30),
        _o("rain", "雨", "rain", 4, when=OUTDOOR),
        _o("snow", "雪", "snow", 3, when=OUTDOOR),
        _o("cherry-blossoms", "樱花", "cherry blossoms", 3, when=OUTDOOR),
        _o("backlighting", "逆光", "backlighting", 3),
        _o("light-particles", "光粒子", "light particles", 2),
    ], when={"not": {"state": "place", "in": ["none"]}}),
]

DRAW_ORDER = [part["id"] for part in PARTITIONS]
PROMPT_ORDER = [
    "subject", "framing", "angle", "gaze", "hair-length", "hairstyle", "bangs", "hair-color",
    "eye-color", "expression", "head", "accessory", "outfit", "top", "outerwear", "bottom",
    "legwear", "shoes", "pose", "hands", "scene", "time", "weather",
]

BASIC_TEMPLATE: dict[str, Any] = {
    "version": 1,
    "resources": {"hands": 2, "top": 1, "bottom": 1},
    "states": {"gender": "性别", "age": "年龄", "pose": "姿势", "hair": "发长",
               "top-color": "上衣颜色", "place": "场所", "time": "时间"},
    "slots": [{"id": "color", "label": "颜色", "values": [
        {"id": id, "tag": tag, "label": label, "weight": weight}
        for id, tag, label, weight in COLORS
    ]}],
    "style_tags": [{"tag": "detailed eyes", "needs": "eyes"},
                   {"tag": "beautiful detailed eyes", "needs": "eyes"},
                   {"tag": "detailed face", "needs": "face"}],
    "glossary": {"detailed eyes": "精细眼睛", "beautiful detailed eyes": "精致眼睛",
                 "detailed face": "精细面部", "geta": "木屐", "hime cut": "姬发式"},
    "draw_order": DRAW_ORDER,
    "prompt_order": PROMPT_ORDER,
    "partitions": PARTITIONS,
    "rules": [
        {"id": "barefoot", "label": "不写鞋时赤脚",
         "when": {"all": [{"chosen": "shoes.none"}, {"visible": "feet"}]},
         "effects": {"content_add": ["barefoot"]}},
        {"id": "night-no-sunlight", "label": "夜晚去掉画风里的阳光",
         "when": {"state": "time", "in": ["night"]},
         "effects": {"style_remove": ["sunlight", "dappled sunlight"]}},
        {"id": "gentle-smile", "label": "微笑柔和化（示例，默认停用）",
         "when": {"any": [{"tag": "smile"}, {"tag": "light smile"}]},
         "effects": {"style_add": ["gentle smile"]}, "disabled": True},
    ],
}


def basic_template() -> DatasetRecipe:
    return DatasetRecipe.model_validate(BASIC_TEMPLATE)
