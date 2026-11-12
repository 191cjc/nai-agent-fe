"""Operator-approved starting recipe: balanced adult women and compatible pose bundles.

This is repository-owned vocabulary, not content copied from a private dataset. All
choices, quotas and cleanup rules remain editable in the ordinary recipe editor.
"""

from typing import Any

from .recipe_engine import DatasetRecipe


def _o(id: str, label: str, tags: str, weight: float = 1, **extra: Any) -> dict:
    return {"id": id, "label": label, "tags": tags, "weight": weight, **extra}


def _none(label: str, weight: float = 1, **extra: Any) -> dict:
    return {"id": "none", "none": True, "label": label, "weight": weight, **extra}


def _p(id: str, label: str, options: list[dict], **extra: Any) -> dict:
    return {"id": id, "label": label, "options": options, **extra}


def _state(key: str, *values: str) -> dict:
    return {"state": key, "in": list(values)}


def _not(condition: dict) -> dict:
    return {"not": condition}


def _pose(
    id: str, label: str, tags: str, group: str, *, floor: bool = False, hide_face: bool = False,
) -> dict:
    complex_pose = group != "ordinary"
    effects: dict[str, Any] = {"set": {"ground-pose": "yes" if floor else "no"}}
    if complex_pose:
        effects["consume"] = {"hands": 2}
        tags += ", hands and feet in frame"
    if hide_face:
        effects["hide"] = ["face"]
    return _o(id, label, tags, when=_state("pose-group", group), effects=effects,
              **({"size": "landscape"} if group in {"lying", "fold", "ground"} else {}))


COLORS = [
    ("white", "white", "白色"), ("black", "black", "黑色"),
    ("red", "red", "红色"), ("navy", "navy blue", "藏青色"),
    ("light-blue", "light blue", "天蓝色"), ("pink", "pink", "粉色"),
    ("purple", "purple", "紫色"), ("green", "green", "绿色"),
]
HAIR_COLORS = [
    ("red", "red hair", "红发"), ("blue", "blue hair", "蓝发"),
    ("dark-blue", "dark blue hair", "深蓝发"),
    ("light-blue", "light blue hair", "天蓝发"),
    ("white", "white hair", "白发"), ("black", "black hair", "黑发"),
    ("blonde", "blonde hair", "金黄发"), ("pink", "pink hair", "粉发"),
]
HAIRSTYLES = [
    ("short-straight", "短直发", "short hair, straight hair"),
    ("bob", "波波头", "short hair, bob cut"),
    ("short-curly", "短卷发", "short hair, curly hair"),
    ("short-wavy", "短波浪发", "short hair, wavy hair"),
    ("medium-straight", "中长直发", "medium hair, straight hair"),
    ("long-straight", "长直发", "long hair, straight hair"),
    ("long-wavy", "长卷发", "long hair, wavy hair"),
    ("high-ponytail", "高马尾", "long hair, high ponytail"),
    ("low-ponytail", "低马尾", "long hair, low ponytail"),
    ("side-ponytail", "侧马尾", "long hair, side ponytail"),
    ("twintails", "双马尾", "long hair, twintails"),
    ("braid", "单辫", "long hair, single braid"),
    ("twin-braids", "双辫", "long hair, twin braids"),
    ("updo", "盘发", "hair up, hair bun"),
    ("double-bun", "双丸子头", "hair up, double bun"),
]
BANGS = [
    ("blunt", "齐刘海", "blunt bangs"), ("parted", "中分", "parted bangs"),
    ("swept", "斜刘海", "swept bangs"),
    ("asymmetrical", "不对称刘海", "asymmetrical bangs"),
    ("crossed", "交叉刘海", "crossed bangs"),
    ("double-parted", "双分刘海", "double-parted bangs"),
    ("long", "长刘海", "long bangs"), ("short", "短刘海", "short bangs"),
    ("between-eyes", "眼间刘海", "hair between eyes"),
    ("over-one-eye", "遮单眼", "hair over one eye"),
]
EYE_COLORS = ["blue", "green", "brown", "red", "yellow", "purple", "grey", "amber"]
EYE_TAGS = [
    *(f"{color} eyes" for color in [*EYE_COLORS, "aqua", "light blue", "pink", "gold", "orange"]),
    "detailed eyes", "beautiful detailed eyes", "beautiful eyes", "sparkling eyes",
    "glowing eyes", "expressive eyes", "wide eyes", "open eyes", "pupils", "iris", "irises",
    "eye highlights", "bright pupils", "constricted pupils", "dilated pupils", "slit pupils",
    "heart-shaped pupils", "star-shaped pupils", "cross-shaped pupils", "heterochromia",
]
GAZE_TAGS = ["looking at viewer", "looking away", "looking up", "looking down", "looking ahead"]
SHOE_TAGS = [
    "shoes", "socks", "boots", "sneakers", "loafers", "sandals", "geta", "flats",
    *(f"{color} {kind}" for _id, color, _label in COLORS
      for kind in ["boots", "sneakers", "loafers", "sandals", "flats"]),
    "white socks", "black socks",
]
EAR_TAGS = ["pointy ears", "long ears", "elf ears"]
HORN_TAGS = ["horns", "demon horns"]
MOUTH_TAGS = ["open mouth", "tongue out", "teeth", "detailed mouth", "detailed tongue"]
SUNLIGHT_TAGS = ["sunlight", "dappled sunlight", "sunlight filtering through trees"]
FOREHEAD_TAGS = ["forehead mark", "forehead markings", "red forehead markings"]
BODY_TAGS = ["large breasts", "small breasts", "medium breasts", "flat chest"]
ORDINARY = _state("pose-group", "ordinary")
SHOD = _state("footwear", "shod")
OUTDOOR = _state("place", "outdoor")

POSES = [
    _pose("standing", "自然站立", "standing", "ordinary"),
    _pose("relaxed-standing", "单腿承重站姿", "standing, weight on one leg", "ordinary"),
    _pose("walking", "行走", "walking", "ordinary"),
    _pose("chair-sitting", "椅坐", "sitting, on chair", "ordinary"),
    _pose("floor-sitting", "地坐", "sitting, on floor", "ordinary", floor=True),
    _pose("seiza", "跪坐", "seiza", "ordinary", floor=True),
    _pose("squatting", "蹲姿", "squatting", "ordinary"),
    _pose("tree", "树式", "yoga, standing on one leg, sole against inner calf, hands together",
          "yoga"),
    _pose("warrior-one", "战士一式",
          "yoga, lunging, front knee bent, back leg extended, arms up", "yoga"),
    _pose("warrior-two", "战士二式",
          "yoga, feet apart, arms out, front knee bent", "yoga"),
    _pose("triangle", "三角伸展",
          "yoga, triangle pose, legs straight, one hand near ankle, other arm up", "yoga"),
    _pose("downward-dog", "下犬式",
          "yoga, downward-facing dog pose, hips raised, hands and feet grounded, "
          "palms spread, spine lengthened, legs straight", "yoga", floor=True),
    _pose("child-pose", "婴儿式",
          "yoga, balasana, child's pose, kneeling, sitting on heels, torso folded forward, "
          "forehead on floor, arms extended forward", "yoga", floor=True, hide_face=True),
    _pose("extended-puppy", "小狗伸展式",
          "yoga, extended puppy pose, knees under hips, hips raised, chest lowered, "
          "arms extended forward, palms on floor", "yoga", floor=True),
    _pose("dolphin", "海豚式",
          "yoga, dolphin pose, forearms on floor, elbows under shoulders, hips raised, "
          "legs straight, feet grounded, spine lengthened", "yoga", floor=True),
    _pose("one-legged-downward-dog", "单腿下犬式",
          "yoga, one-legged downward-facing dog pose, palms on floor, hips raised, "
          "one foot grounded, other leg extended upward, spine lengthened", "yoga", floor=True),
    _pose("cat", "猫式",
          "yoga, cat pose, all fours, palms under shoulders, knees under hips, "
          "back rounded upward, chin tucked", "yoga", floor=True),
    _pose("cow", "牛式",
          "yoga, cow pose, all fours, palms under shoulders, knees under hips, "
          "back arched downward, chest lifted, head raised", "yoga", floor=True),
    _pose("cobra", "眼镜蛇式",
          "yoga, lying, on stomach, palms beneath shoulders, chest raised", "yoga", floor=True),
    _pose("bridge", "桥式",
          "yoga, lying, on back, knees bent, feet on floor, hips raised", "yoga", floor=True),
    _pose("seated-twist", "坐姿扭转",
          "yoga, sitting, seated twist, one knee bent, torso turned", "yoga", floor=True),
    _pose("gate", "门闩式",
          "yoga, kneeling, one leg extended to side, leaning to side, one arm overhead", "yoga"),
    _pose("fighting-ready", "格斗准备",
          "fighting stance, feet apart, knees bent, fists raised", "combat"),
    _pose("punch", "出拳",
          "punching, one fist extended, other fist near chest, torso turned", "combat"),
    _pose("block", "格挡", "fighting stance, blocking, crossed forearms, knees bent", "combat"),
    _pose("side-kick", "侧踢", "kicking, leg extended to side, arms out, balancing", "combat"),
    _pose("high-kick", "高踢", "high kick, one leg raised, arms out, balancing", "combat"),
    _pose("combat-lunge", "弓步", "fighting stance, lunging, front knee bent, fists raised",
          "combat"),
    _pose("dodge", "闪避", "dodging, lunging to side, torso lowered, arms bent", "combat"),
    _pose("low-guard", "低位蹲守", "crouching, one knee near ground, hands raised", "combat"),
    _pose("prone", "俯卧", "lying, on stomach, head raised, elbows on floor", "lying", floor=True),
    _pose("supine", "仰卧", "lying, on back, arms out", "lying", floor=True),
    _pose("side-lying", "侧卧", "lying, on side, supported on elbow, knees bent", "lying",
          floor=True),
    _pose("bent-knee-lying", "屈膝仰卧", "lying, on back, knees bent, feet on floor", "lying",
          floor=True),
    _pose("seated-fold", "坐位体前屈",
          "sitting, seated forward fold, legs extended, feet together, hands reaching for toes",
          "fold", floor=True),
    _pose("seated-reach", "坐姿尝试碰脚尖",
          "sitting, legs extended, leaning forward, fingertips near toes", "fold", floor=True),
    _pose("single-leg-fold", "单腿前屈",
          "sitting, one leg extended, other knee bent, hands reaching for toes",
          "fold", floor=True),
    _pose("standing-fold", "站立前屈",
          "standing, bent over, legs straight, hands reaching for toes", "fold"),
    _pose("ankle-reach", "手触脚踝",
          "sitting, seated forward fold, legs extended, hands holding ankles", "fold", floor=True),
    _pose("all-fours", "四肢着地",
          "all fours, palms under shoulders, knees under hips, back straight",
          "ground", floor=True),
    _pose("crawling", "爬行", "crawling, opposite hand and knee forward", "ground", floor=True),
    _pose("one-hand-reach", "单手前伸支撑",
          "all fours, one hand reaching forward, knees on floor", "ground", floor=True),
    _pose("plank", "平板支撑", "plank, palms under shoulders, legs extended, back straight",
          "ground", floor=True),
    _pose("side-plank", "侧平板支撑",
          "side plank, supported on one hand, legs extended, other arm up", "ground", floor=True),
    _pose("reverse-plank", "反向平板",
          "reverse plank, face up, palms on floor behind torso, arms straight, legs extended, "
          "heels grounded, hips raised, torso aligned with legs", "ground", floor=True),
]

PARTITIONS = [
    _p("subject", "主体", [_o("woman", "成年女性", "1girl, solo, adult woman",
                             effects={"set": {"gender": "female", "age": "adult"}})], quota=True),
    _p("pose-group", "动作类别", [
        _o("yoga", "瑜伽", "yoga", 43.75, effects={"set": {"pose-group": "yoga"}}),
        _o("combat", "战斗姿态", "fighting stance", 26.25,
           effects={"set": {"pose-group": "combat"}}),
        _o("ordinary", "普通姿态", "solo", 12.5,
           effects={"set": {"pose-group": "ordinary"}}),
        _o("lying", "卧姿", "lying", 5, effects={"set": {"pose-group": "lying"}}),
        _o("fold", "前屈与碰脚尖", "stretching", 7.5,
           effects={"set": {"pose-group": "fold"}}),
        _o("ground", "四肢与支撑", "exercise", 5,
           effects={"set": {"pose-group": "ground"}}),
    ], quota=True),
    _p("framing", "景别", [
        _o("close-up", "脸部特写", "close-up, face focus", when=ORDINARY,
           effects={"hide": ["upper", "lower", "hands"]}),
        _o("portrait", "肖像", "portrait", when=ORDINARY,
           effects={"hide": ["lower", "hands"]}),
        _o("upper-body", "上半身", "upper body", when=ORDINARY,
           effects={"hide": ["lower"]}),
        _o("cowboy-shot", "七分身", "cowboy shot", when=ORDINARY,
           effects={"hide": ["feet"]}, size="portrait"),
        _o("full-body", "全身", "full body", size="portrait"),
        _o("wide-shot", "远景全身", "full body, wide shot", when=ORDINARY,
           effects={"hide": ["eyes"]}, size="landscape"),
    ], quota=True),
    _p("pose", "具体动作", POSES, quota=True),
    _p("direction", "观察方向", [
        _o("front", "正面", "front view", effects={"set": {"view": "front"}}),
        _o("front-left", "左前斜侧", "three-quarter view, facing left",
           effects={"set": {"view": "front"}}),
        _o("front-right", "右前斜侧", "three-quarter view, facing right",
           effects={"set": {"view": "front"}}),
        _o("left", "左侧面", "from side, profile, facing left",
           effects={"set": {"view": "side"}}),
        _o("right", "右侧面", "from side, profile, facing right",
           effects={"set": {"view": "side"}}),
        _o("back-left", "左后斜侧", "from behind, rear three-quarter view, facing left",
           effects={"hide": ["face"], "set": {"view": "back"}, "remove_tags": ["face focus"]}),
        _o("back-right", "右后斜侧", "from behind, rear three-quarter view, facing right",
           effects={"hide": ["face"], "set": {"view": "back"}, "remove_tags": ["face focus"]}),
        _o("back", "背面", "from behind",
           effects={"hide": ["face"], "set": {"view": "back"}, "remove_tags": ["face focus"]}),
    ], quota=True),
    _p("elevation", "机位高度", [
        _none("平视"), _o("above", "轻俯视", "from above"),
        _o("overhead", "强俯视", "from above, overhead view"),
        _o("below", "轻仰视", "from below", when=_not(_state("ground-pose", "yes"))),
        _o("low", "强仰视", "from below, foreshortening",
           when=_not(_state("ground-pose", "yes"))),
    ], quota=True),
    _p("roll", "镜头倾斜", [_none("正常镜头", 90),
                         _o("dutch", "倾斜构图", "dutch angle", 10)], quota=True),
    _p("fantasy", "异形特征", [
        _none("普通外貌", 80, effects={"set": {"fantasy": "ordinary"}}),
        _o("long-ears", "精灵长尖耳", "pointy ears, long ears", 10,
           effects={"set": {"fantasy": "elf"}, "style_remove": ["round ears"]}),
        _o("demon-horns", "恶魔角", "demon horns", 10,
           effects={"set": {"fantasy": "horns"}}),
    ], quota=True, needs=["head"]),
    _p("hairstyle", "发型", [_o(id, label, tags) for id, label, tags in HAIRSTYLES],
       quota=True, needs=["head"]),
    _p("bangs", "刘海", [
        _o(id, label, f"6::{tag}::", effects={
            "set": {"eye-view": "one" if id == "over-one-eye" else "both"},
            **({"hide": ["forehead"]} if id not in {"parted", "double-parted"} else {}),
        }) for id, label, tag in BANGS
    ], quota=True, needs=["face"]),
    _p("hair-color", "发色", [
        _o(id, label, tag if id in {"white", "black"} else f"3::{tag}::",
           effects={"style_remove": [other for _id, other, _label in HAIR_COLORS if other != tag]})
        for id, tag, label in HAIR_COLORS
    ], quota=True, needs=["head"]),
    _p("skin", "肤色", [_none("不填肤色", 90, effects={
        "style_remove": ["dark skin", "dark-skinned female"],
    }), _o("dark", "深色肤色", "dark skin", 10)],
       quota=True),
    _p("body-type", "体型", [
        _o(id, label, tag, weight,
           effects={"style_remove": [other for other in BODY_TAGS if other != tag]})
        for id, label, tag, weight in [
            ("large-breasts", "较大胸型", "large breasts", 80),
            ("medium-breasts", "中等胸型", "medium breasts", 10),
            ("small-breasts", "较小胸型", "small breasts", 10),
        ]
    ], quota=True, needs=["upper"], when=_state("age", "adult")),
    _p("expression", "表情", [
        _o("smile", "微笑", "smile, closed mouth", effects={"hide": ["mouth-interior"]}),
        _o("light-smile", "浅笑", "light smile, closed mouth",
           effects={"hide": ["mouth-interior"]}),
        _o("laughing", "大笑", "laughing, open mouth"),
        _o("serious", "严肃", "serious, closed mouth", effects={"hide": ["mouth-interior"]}),
        _o("calm", "平静", "calm, closed mouth", effects={"hide": ["mouth-interior"]}),
        _o("relaxed", "放松", "relaxed expression, closed mouth",
           effects={"hide": ["mouth-interior"]}),
        _o("surprised", "惊讶", "surprised, open mouth"),
        _o("angry", "生气", "angry, closed mouth", effects={"hide": ["mouth-interior"]}),
        _o("sad", "难过", "sad, closed mouth", effects={"hide": ["mouth-interior"]}),
        _o("smirk", "得意笑", "smirk, closed mouth", effects={"hide": ["mouth-interior"]}),
        _o("expressionless", "面无表情", "expressionless, closed mouth",
           effects={"hide": ["mouth-interior"]}),
        _o("closed-eyes", "闭眼微笑", "closed eyes, smile, closed mouth", effects={
            "hide": ["eyes", "mouth-interior"], "remove_partitions": ["eye-color", "gaze"],
            "set": {"eye-view": "closed"},
        }),
        _o("wink", "眨眼", "wink, smile, closed mouth", effects={
            "hide": ["mouth-interior"], "set": {"eye-view": "one"},
        }),
    ], quota=True, needs=["face"]),
    _p("eye-color", "瞳色", [_o(color, f"{color} 瞳色", f"{color} eyes")
                            for color in EYE_COLORS], quota=True, needs=["eyes"]),
    _p("gaze", "视线", [
        _o("viewer", "看镜头", "looking at viewer", when=_state("view", "front")),
        _o("away", "看别处", "looking away"), _o("up", "向上看", "looking up"),
        _o("down", "向下看", "looking down"), _o("ahead", "看前方", "looking ahead"),
    ], quota=True, needs=["eyes"]),
    _p("outfit-family", "服装类别", [
        _o("kimono", "和服", "kimono", effects={"set": {"outfit-family": "kimono"}}),
        _o("chinese", "中国服装", "chinese clothes",
           effects={"set": {"outfit-family": "chinese"}}),
        _o("dress", "连衣裙", "dress", effects={"set": {"outfit-family": "dress"}}),
        _o("arabian", "阿拉伯服装", "harem outfit",
           effects={"set": {"outfit-family": "arabian"}}),
        _o("school", "校服", "school uniform", effects={"set": {"outfit-family": "school"}}),
        _o("cheer", "啦啦队服", "cheerleader", effects={"set": {"outfit-family": "cheer"}}),
    ], quota=True, needs=["upper"]),
    _p("outfit", "服装款式", [
        _o("kimono", "{color}和服", "{color} kimono, obi", when=_state("outfit-family", "kimono"),
           effects={"consume": {"top": 1, "bottom": 1},
                    "allow_options": {"shoes": ["geta"]},
                    "remove_partitions": ["bottom", "legwear"]}),
        _o("hanfu", "{color}汉服", "{color} hanfu", when=_state("outfit-family", "chinese"),
           effects={"consume": {"top": 1, "bottom": 1},
                    "remove_partitions": ["bottom", "legwear"]}),
        _o("china-dress", "{color}旗袍", "{color} china dress",
           when=_state("outfit-family", "chinese"), slots={"color": {"exclude": ["green"]}},
           effects={"consume": {"top": 1, "bottom": 1}, "remove_partitions": ["bottom"]}),
        _o("dress", "{color}连衣裙", "{color} dress", when=_state("outfit-family", "dress"),
           effects={"consume": {"top": 1, "bottom": 1}, "remove_partitions": ["bottom"]}),
        _o("long-dress", "{color}长连衣裙", "{color} dress, long dress",
           when=_state("outfit-family", "dress"),
           effects={"consume": {"top": 1, "bottom": 1},
                    "remove_partitions": ["bottom", "legwear"]}),
        _o("sundress", "{color}吊带连衣裙", "{color} sundress",
           when=_state("outfit-family", "dress"),
           effects={"consume": {"top": 1, "bottom": 1}, "remove_partitions": ["bottom"]}),
        _o("arabian", "{color}阿拉伯风格上装", "{color} harem outfit",
           when=_state("outfit-family", "arabian"),
           slots={"color": {"set_state": "top-color"}},
           effects={"consume": {"top": 1},
                    "allow_options": {"bottom": ["pelvic-curtain", "harem-pants"]}}),
        _o("serafuku", "{color}水手服", "{color} serafuku",
           when=_state("outfit-family", "school"),
           slots={"color": {"set_state": "top-color"}},
           effects={"consume": {"top": 1}, "allow_options": {"bottom": ["pleated-skirt"]}}),
        _o("school-shirt", "{color}校服衬衫", "{color} collared shirt",
           when=_state("outfit-family", "school"),
           slots={"color": {"set_state": "top-color"}},
           effects={"consume": {"top": 1}, "allow_options": {"bottom": ["pleated-skirt"]}}),
        _o("cheer", "{color}啦啦队服", "{color} cheerleader uniform",
           when=_state("outfit-family", "cheer"),
           slots={"color": {"set_state": "top-color"}},
           effects={"consume": {"top": 1}, "allow_options": {"bottom": ["pleated-skirt"]}}),
    ], quota=True, needs=["upper"]),
    _p("bottom", "下装", [
        _o("pleated-skirt", "{color}百褶裙", "{color} pleated skirt",
           effects={"consume": {"bottom": 1}},
           slots={"color": {"exclude_state": "top-color"}}),
        _o("pelvic-curtain", "{color}帘状裙", "{color} pelvic curtain",
           effects={"consume": {"bottom": 1}},
           slots={"color": {"exclude_state": "top-color"}}),
        _o("harem-pants", "{color}灯笼裤", "{color} harem pants",
           effects={"consume": {"bottom": 1}, "remove_partitions": ["legwear"]},
           slots={"color": {"exclude_state": "top-color"}}),
    ], quota=True, needs=["lower"]),
    _p("footwear-status", "鞋袜状态", [
        _o("barefoot", "赤脚", "barefoot", 70, effects={
            "set": {"footwear": "barefoot"}, "remove_partitions": ["shoes", "legwear"],
        }),
        _none("穿鞋", 30, effects={"set": {"footwear": "shod"}}),
    ], quota=True, needs=["feet"]),
    _p("shoes", "鞋子", [
        _o("geta", "木屐", "geta", when=_state("outfit-family", "kimono")),
        *[_o(id, label, f"{{color}} {tag}", when=_not(_state("outfit-family", "kimono")))
          for id, label, tag in [
              ("loafers", "{color}乐福鞋", "loafers"),
              ("sneakers", "{color}运动鞋", "sneakers"),
              ("sandals", "{color}凉鞋", "sandals"),
              ("boots", "{color}短靴", "boots"),
              ("flats", "{color}平底鞋", "flats"),
          ]],
    ], quota=True, needs=["feet"], when=SHOD),
    _p("legwear", "袜子", [
        _none("不写袜子"), _o("white-socks", "白袜", "white socks"),
        _o("black-socks", "黑袜", "black socks"),
    ], quota=True, needs=["feet"], when=SHOD),
    _p("hands", "额外手部动作", [
        _none("不加手势", 4),
        _o("waving", "挥手", "waving", effects={"consume": {"hands": 1}}),
        _o("together", "双手合拢", "hands together", effects={"consume": {"hands": 2}}),
        _o("hips", "双手叉腰", "hands on own hips", effects={"consume": {"hands": 2}}),
        _o("cup", "拿杯子", "holding cup", effects={"consume": {"hands": 1}}),
    ], mode="fill", max_draws=2, needs=["hands"], when=ORDINARY),
    _p("accessory", "饰品", [
        _none("无饰品", 4), _o("ribbon", "{color}发带", "{color} hair ribbon"),
        _o("earrings", "耳环", "earrings", needs=["ears"]),
        _o("glasses", "眼镜", "glasses", needs=["face"]),
        _o("beret", "{color}贝雷帽", "{color} beret",
           when=_not(_state("fantasy", "horns")), effects={"hide": ["forehead"]}),
    ], needs=["head"]),
    _p("forehead-mark", "额头印记", [
        _none("不加印记", 90, effects={"style_remove": FOREHEAD_TAGS}),
        _o("red-mark", "红色额头印记", "forehead mark, red forehead markings", 10),
    ], quota=True, needs=["forehead"]),
    _p("scene", "背景", [
        _o("simple", "纯色背景", "simple background", effects={"set": {"place": "none"}}),
        *[_o(id, label, tags, effects={"set": {"place": place}}) for id, label, tags, place in [
            ("japanese-garden", "日式庭院", "japanese garden, outdoors", "outdoor"),
            ("chinese-garden", "中式庭院", "chinese courtyard, outdoors", "outdoor"),
            ("classroom", "教室", "classroom, indoors", "indoor"),
            ("library", "图书馆", "library, indoors", "indoor"),
            ("cafe", "咖啡馆", "cafe, indoors", "indoor"),
            ("studio", "练习室", "practice room, indoors", "indoor"),
            ("street", "城市街道", "street, outdoors", "outdoor"),
            ("park", "公园", "park, outdoors", "outdoor"),
            ("forest", "森林", "forest, outdoors", "outdoor"),
            ("beach", "海边", "beach, outdoors", "outdoor"),
            ("desert", "沙漠庭院", "desert courtyard, outdoors", "outdoor"),
        ]],
    ], quota=True),
    _p("time", "时间", [
        _o("day", "白昼", "day", effects={"set": {"time": "day"}}),
        _o("sunset", "黄昏", "sunset", effects={"set": {"time": "sunset"}}),
        _o("night", "夜晚", "night", effects={"set": {"time": "night"}}),
    ], quota=True, when=_not(_state("place", "none"))),
    _p("weather", "天气", [
        _none("不写天气", 3), _o("rain", "下雨", "rain", when=OUTDOOR),
        _o("snow", "下雪", "snow", when=OUTDOOR),
        _o("petals", "樱花", "cherry blossoms", when=OUTDOOR),
    ], when=OUTDOOR),
]

REGIONS = [
    {"id": "person", "label": "人物"},
    {"id": "head", "label": "头部", "parent": "person"},
    {"id": "face", "label": "脸", "parent": "head"},
    {"id": "forehead", "label": "额头", "parent": "face"},
    {"id": "eyes", "label": "眼球", "parent": "face"},
    {"id": "mouth-interior", "label": "口腔内部", "parent": "face"},
    {"id": "ears", "label": "耳朵", "parent": "head"},
    {"id": "horns", "label": "角", "parent": "head"},
    {"id": "upper", "label": "上身", "parent": "person"},
    {"id": "lower", "label": "下身", "parent": "person"},
    {"id": "feet", "label": "脚", "parent": "lower"},
    {"id": "hands", "label": "手", "parent": "person"},
]
DRAW_ORDER = [part["id"] for part in PARTITIONS]
PROMPT_ORDER = [
    "subject", "framing", "direction", "elevation", "roll", "fantasy", "hairstyle", "bangs",
    "hair-color", "skin", "body-type", "forehead-mark", "expression", "eye-color", "gaze",
    "outfit-family", "outfit", "bottom",
    "footwear-status", "shoes", "legwear", "pose-group", "pose", "hands", "accessory", "scene",
    "time", "weather",
]

# Bind only details that require the actual visible part. Eyelashes, eyebrows, glasses
# and the closed-eyes instruction itself deliberately do not depend on visible eyeballs.
STYLE_TAGS = [
    *[{"tag": tag, "needs": "eyes"} for tag in [*EYE_TAGS, *GAZE_TAGS]],
    *[{"tag": tag, "needs": "face"}
      for tag in ["detailed face", "beautiful detailed face", "relaxed expression"]],
    *[{"tag": tag, "needs": "forehead"} for tag in FOREHEAD_TAGS],
    *[{"tag": tag, "needs": "upper"} for tag in BODY_TAGS],
    *[{"tag": tag, "needs": "mouth-interior"} for tag in MOUTH_TAGS],
    *[{"tag": tag, "needs": "hands"}
      for tag in ["detailed hands", "beautiful hands", "nail polish"]],
    *[{"tag": tag, "needs": "feet"}
      for tag in ["detailed feet", "toes", "toenail polish", "barefoot", *SHOE_TAGS]],
    *[{"tag": tag, "needs": "ears"} for tag in EAR_TAGS],
    *[{"tag": tag, "needs": "horns"} for tag in HORN_TAGS],
]

GLOSSARY = {
    "long ears": "长耳", "round ears": "圆耳", "exercise": "支撑动作", "stretching": "拉伸",
    "facing left": "朝左", "facing right": "朝右", "overhead view": "正上方俯视",
    "harem outfit": "阿拉伯风格服装", "harem pants": "灯笼裤", "hanfu": "汉服",
    "cheerleader uniform": "啦啦队服", "long dress": "长连衣裙", "flats": "平底鞋",
    "practice room": "练习室", "japanese garden": "日式庭院",
    "chinese courtyard": "中式庭院", "desert courtyard": "沙漠庭院",
    "detailed eyes": "精细眼睛", "beautiful detailed eyes": "精致眼睛",
    "detailed face": "精细面部", "detailed hands": "精细手部", "detailed feet": "精细脚部",
    "open eyes": "睁眼", "short bangs": "短刘海", "hair up": "盘起头发",
    "high ponytail": "高马尾", "low ponytail": "低马尾", "single braid": "单辫",
    "double bun": "双丸子头", "heterochromia": "异色瞳", "grey eyes": "灰瞳",
    "beautiful detailed face": "精致面部", "beautiful eyes": "美丽眼睛",
    "beautiful hands": "美丽双手", "detailed mouth": "精细嘴部",
    "detailed tongue": "精细舌部", "dilated pupils": "扩张瞳孔", "elf ears": "精灵耳",
    "expressive eyes": "传神眼睛", "eye highlights": "眼部高光", "wide eyes": "睁大眼睛",
    "iris": "虹膜", "irises": "虹膜", "pupils": "瞳孔",
    "adult woman": "成年女性", "relaxed expression": "放松表情",
    "large breasts": "较大胸型", "small breasts": "较小胸型",
    "medium breasts": "中等胸型", "flat chest": "平胸",
    "forehead mark": "额头印记", "forehead markings": "额头印记",
    "red forehead markings": "红色额头印记", "rear three-quarter view": "后侧四分之三视角",
    "downward-facing dog pose": "下犬式", "hands and feet grounded": "双手双脚着地",
    "palms spread": "手掌展开", "spine lengthened": "脊柱伸展",
    "balasana": "婴儿式", "child's pose": "婴儿式", "sitting on heels": "坐在脚跟上",
    "torso folded forward": "躯干前折", "forehead on floor": "额头贴地",
    "arms extended forward": "双臂前伸", "extended puppy pose": "小狗伸展式",
    "chest lowered": "胸部下沉", "dolphin pose": "海豚式",
    "forearms on floor": "前臂着地", "elbows under shoulders": "肘部位于肩下",
    "feet grounded": "双脚着地", "one-legged downward-facing dog pose": "单腿下犬式",
    "one foot grounded": "单脚着地", "other leg extended upward": "另一腿向上伸展",
    "cat pose": "猫式", "back rounded upward": "背部向上拱起", "chin tucked": "收下巴",
    "cow pose": "牛式", "back arched downward": "背部向下弯曲", "chest lifted": "抬胸",
    "reverse plank": "反向平板", "face up": "面朝上", "heels grounded": "脚跟着地",
    "palms on floor behind torso": "双手在躯干后方撑地", "arms straight": "双臂伸直",
    "torso aligned with legs": "躯干与双腿保持直线",
    **{f"{color} {kind}": f"{label}{zh}" for _id, color, label in COLORS
       for kind, zh in [("boots", "靴子"), ("sneakers", "运动鞋"), ("loafers", "乐福鞋"),
                        ("sandals", "凉鞋"), ("flats", "平底鞋")]},
}

BASIC_TEMPLATE: dict[str, Any] = {
    "version": 1, "regions": REGIONS, "resources": {"hands": 2, "top": 1, "bottom": 1},
    "states": {
        "gender": "性别", "age": "年龄", "pose-group": "动作类别", "ground-pose": "地面动作",
        "view": "朝向", "fantasy": "异形特征", "eye-view": "眼睛可见状态",
        "outfit-family": "服装类别", "top-color": "上衣颜色", "footwear": "鞋袜状态",
        "place": "场所", "time": "时间",
    },
    "slots": [{"id": "color", "label": "颜色", "values": [
        {"id": id, "tag": tag, "label": label, "weight": 1} for id, tag, label in COLORS
    ]}],
    "style_tags": STYLE_TAGS, "glossary": GLOSSARY, "draw_order": DRAW_ORDER,
    "prompt_order": PROMPT_ORDER, "partitions": PARTITIONS,
    # Cleanup rules are last so ordinary additions cannot reintroduce forbidden details.
    "rules": [
        {"id": "ordinary-features", "label": "普通外貌移除长耳与角",
         "when": _state("fantasy", "ordinary"),
         "effects": {"remove_tags": [*EAR_TAGS, *HORN_TAGS],
                     "style_remove": [*EAR_TAGS, *HORN_TAGS]}},
        {"id": "elf-features", "label": "长耳外貌移除角",
         "when": _state("fantasy", "elf"),
         "effects": {"remove_tags": HORN_TAGS, "style_remove": HORN_TAGS}},
        {"id": "horn-features", "label": "有角外貌移除长耳",
         "when": _state("fantasy", "horns"),
         "effects": {"remove_tags": EAR_TAGS, "style_remove": EAR_TAGS}},
        {"id": "one-eye", "label": "单眼可见时不描述双眼特征",
         "when": {"any": [_state("eye-view", "one"), _state("view", "side")]},
         "effects": {"remove_tags": ["heterochromia"], "style_remove": ["heterochromia"]}},
        {"id": "closed-eyes", "label": "闭眼时移除眼球与视线描述",
         "when": {"chosen": "expression.closed-eyes"},
         "effects": {"remove_tags": [*EYE_TAGS, *GAZE_TAGS]}},
        {"id": "closed-mouth", "label": "闭嘴时移除口腔细节",
         "when": {"not": {"visible": "mouth-interior"}},
         "effects": {"remove_tags": MOUTH_TAGS, "style_remove": MOUTH_TAGS}},
        {"id": "barefoot", "label": "赤脚时移除鞋袜",
         "when": _state("footwear", "barefoot"),
         "effects": {"remove_partitions": ["shoes", "legwear"],
                     "remove_tags": SHOE_TAGS, "style_remove": SHOE_TAGS}},
        {"id": "shod", "label": "穿鞋时移除赤脚与脚趾细节",
         "when": SHOD,
         "effects": {"remove_tags": ["barefoot", "toes", "toenail polish"],
                     "style_remove": ["barefoot", "toes", "toenail polish"]}},
        {"id": "night-no-sunlight", "label": "夜晚移除阳光",
         "when": _state("time", "night"),
         "effects": {"remove_tags": SUNLIGHT_TAGS,
                     "style_remove": SUNLIGHT_TAGS}},
    ],
}


def basic_template() -> DatasetRecipe:
    return DatasetRecipe.model_validate(BASIC_TEMPLATE)
