"""Pure recipe engine: validation, conflicts, removal, slots, rules and style edits.

Everything here uses invented synthetic recipes; no dataset content is read.
"""

import copy
from collections import Counter

import pytest
from pydantic import ValidationError

from novelai_api.recipe_engine import DatasetRecipe, resolve_style, sample, tag_key


def opt(id, tags="", weight=1, **extra):
    return {"id": id, "label": id, "tags": tags, "weight": weight, **extra}


def none(weight=1, **extra):
    return {"id": "none", "none": True, "label": "无", "weight": weight, **extra}


def part(id, options, **extra):
    return {"id": id, "label": id, "options": options, **extra}


def base_recipe() -> dict:
    partitions = [
        part("scene", [
            opt("room", "indoors, bedroom", 6),
            opt("street", "no humans, street, scenery", 2,
                effects={"hide": ["person"]}, size="landscape"),
        ]),
        part("framing", [
            opt("portrait", "portrait", 1, effects={"hide": ["upper", "lower", "hands"]}),
            opt("upper", "upper body", 1, effects={"hide": ["lower"]}),
            opt("full", "full body", 1, size="portrait"),
        ], needs=["person"]),
        part("view", [
            opt("front", "looking at viewer", 3),
            opt("back", "from behind", 1, effects={"hide": ["face"]}),
        ], needs=["person"]),
        part("subject", [
            opt("girl", "1girl, solo", 1, effects={"set": {"gender": "female", "age": "adult"}}),
        ], needs=["person"]),
        part("hair-length", [
            opt("short", "short hair", 1, effects={"set": {"hair": "short"}}),
            opt("long", "long hair", 1, effects={"set": {"hair": "long"}}),
        ], needs=["person"]),
        part("hairstyle", [
            opt("twintails", "twintails", 1,
                when={"not": {"state": "hair", "in": ["short"]}}),
            opt("loose", "hair down", 1),
        ], needs=["person"]),
        part("expression", [
            opt("smile", "smile", 2),
            opt("closed", "closed eyes, smile", 1,
                effects={"remove_partitions": ["eye-color"], "hide": ["eyes"]}),
            opt("serious", "serious", 1),
        ], needs=["face"]),
        part("eye-color", [opt("blue", "blue eyes"), opt("red", "red eyes")], needs=["eyes"]),
        part("outfit", [
            opt("uniform", "school uniform, serafuku", 2,
                effects={"consume": {"top": 1},
                         "allow_options": {"bottom": ["pleated"]}}),
            opt("dress", "{color} china dress", 2,
                slots={"color": {"exclude": ["green"]}},
                effects={"consume": {"top": 1, "bottom": 1}}),
            none(3),
        ], needs=["upper"]),
        part("top", [
            opt("shirt", "{color} shirt", 1, effects={"consume": {"top": 1}},
                slots={"color": {"set_state": "top-color"}}),
            none(1),
        ], needs=["upper"]),
        part("bottom", [
            opt("pleated", "{color} pleated skirt", 1, effects={"consume": {"bottom": 1}},
                slots={"color": {"exclude_state": "top-color"}}),
            opt("jeans", "blue jeans", 1, effects={"consume": {"bottom": 1}}),
            opt("shorts", "{color} shorts", 1, effects={"consume": {"bottom": 1}}),
        ], needs=["lower"]),
        part("shoes", [opt("boots", "brown boots", 1), none(1)], needs=["feet"]),
        part("hands", [
            opt("two-hand", "holding sword, two-handed", 1, effects={"consume": {"hands": 2}}),
            opt("wave", "waving", 1, effects={"consume": {"hands": 1}}),
            opt("cup", "holding cup", 1, effects={"consume": {"hands": 1}}),
            none(1),
        ], needs=["hands"], mode="fill", max_draws=2),
        part("time", [
            opt("day", "day", 1),
            opt("night", "night", 1, effects={"set": {"time": "night"}}),
        ]),
    ]
    order = [p["id"] for p in partitions]
    return {
        "resources": {"hands": 2, "top": 1, "bottom": 1},
        "slots": [{"id": "color", "label": "颜色", "values": [
            {"id": "white", "tag": "white", "label": "白", "weight": 1},
            {"id": "red", "tag": "red", "label": "红", "weight": 1},
            {"id": "green", "tag": "green", "label": "绿", "weight": 1},
            {"id": "navy", "tag": "navy blue", "label": "藏青", "weight": 1},
        ]}],
        "style_tags": [{"tag": "detailed eyes", "needs": "eyes"}],
        "draw_order": order,
        "prompt_order": ["subject", "framing", "view", "hair-length", "hairstyle", "eye-color",
                         "expression", "outfit", "top", "bottom", "shoes", "hands", "scene",
                         "time"],
        "partitions": partitions,
        "rules": [
            {"id": "gentle", "label": "笑容柔和化", "when": {"tag": "smile"},
             "effects": {"style_add": ["gentle smile"]}},
            {"id": "night-sun", "when": {"state": "time", "in": ["night"]},
             "effects": {"style_remove": ["sunlight"]}},
            {"id": "barefoot",
             "when": {"all": [{"chosen": "shoes.none"}, {"visible": "feet"}]},
             "effects": {"content_add": ["barefoot"]}},
        ],
    }


@pytest.fixture(scope="module")
def recipe() -> DatasetRecipe:
    return DatasetRecipe.model_validate(base_recipe())


@pytest.fixture(scope="module")
def big(recipe):
    return sample(recipe, 400, 7)


def tags_of(item) -> set[str]:
    return {tag_key(tag) for tag in item.prompt.split(",")}


def chosen(item, partition):
    return [d["option"] for d in item.draws if d["partition"] == partition
            and not d["option"].startswith("-")]


def test_same_recipe_seed_and_n_reproduce_exactly(recipe):
    assert sample(recipe, 50, 123) == sample(recipe, 50, 123)
    assert sample(recipe, 50, 123).items != sample(recipe, 50, 124).items


def test_no_human_skips_every_person_partition_and_eye_style(big):
    empty = [item for item in big.items if "street" in chosen(item, "scene")]
    assert empty
    for item in empty:
        assert tags_of(item) & {"1girl", "solo", "smile", "full body"} == set()
        assert "detailed eyes" in item.style_edits["remove"]
        assert item.shape == "landscape"
        skipped = {d["partition"] for d in item.draws if d["option"] == "-skip"}
        assert {"framing", "subject", "expression", "hands"} <= skipped


def test_visibility_upper_and_portrait_never_draw_lower_body(big):
    for item in big.items:
        framing = chosen(item, "framing")
        if framing and framing[0] in ("portrait", "upper"):
            assert not chosen(item, "bottom") and not chosen(item, "shoes")
            assert "barefoot" not in tags_of(item)
        if framing == ["portrait"]:
            assert not chosen(item, "hands") and not chosen(item, "outfit")


def test_back_view_has_no_expression_or_eye_colour(big):
    backs = [item for item in big.items if chosen(item, "view") == ["back"]]
    assert backs
    for item in backs:
        assert not chosen(item, "expression") and not chosen(item, "eye-color")
        assert "detailed eyes" in item.style_edits["remove"]


def test_closed_eyes_removes_eye_colour(big):
    closed = [item for item in big.items if chosen(item, "expression") == ["closed"]]
    assert closed
    for item in closed:
        assert not chosen(item, "eye-color")
        assert not tags_of(item) & {"blue eyes", "red eyes"}


def test_hand_resources(big):
    combos = Counter()
    for item in big.items:
        hands = chosen(item, "hands")
        assert len(hands) <= 2
        if "two-hand" in hands:
            assert hands == ["two-hand"]
        combos[len([h for h in hands if h != "none"])] += 1
    assert combos[2] > 0  # two one-hand actions do co-occur


def test_outfit_consumes_top_and_bottom_and_whitelists_pleated(big):
    for item in big.items:
        outfit = chosen(item, "outfit")
        if outfit and outfit[0] in ("uniform", "dress"):
            assert not chosen(item, "top")
        if outfit == ["dress"]:
            assert not chosen(item, "bottom")
        if outfit == ["uniform"] and chosen(item, "framing") == ["full"]:
            assert chosen(item, "bottom") == ["pleated"]


def test_slots_fill_one_tag_and_respect_exclusions(big):
    dresses = [item for item in big.items if chosen(item, "outfit") == ["dress"]]
    assert dresses
    colours = Counter()
    for item in dresses:
        draw = next(d for d in item.draws if d["partition"] == "outfit")
        colours[draw["values"]["color"]] += 1
        assert f"{dict(white='white', red='red', navy='navy blue')[draw['values']['color']]}" \
            " china dress" in item.prompt
    assert "green" not in colours and len(colours) == 3


def test_exclude_state_prevents_same_top_and_bottom_colour(big):
    for item in big.items:
        top = [d for d in item.draws if d["partition"] == "top" and d["option"] == "shirt"]
        bottom = [d for d in item.draws if d["partition"] == "bottom"
                  and d["option"] == "pleated"]
        if top and bottom:
            assert top[0]["values"]["color"] != bottom[0]["values"]["color"]


def test_state_condition_twintails_never_with_short_hair(big):
    for item in big.items:
        if chosen(item, "hair-length") == ["short"]:
            assert chosen(item, "hairstyle") != ["twintails"]


def test_rules_style_add_and_content_add(big):
    for item in big.items:
        has_smile = "smile" in tags_of(item)
        assert ("gentle smile" in item.style_edits["add"]) == has_smile
        assert "gentle smile" not in tags_of(item)
        if chosen(item, "time") == ["night"]:
            assert "sunlight" in item.style_edits["remove"]
        if chosen(item, "shoes") == ["none"]:
            assert "barefoot" in tags_of(item)


def test_prompt_order_differs_from_draw_order(big):
    item = next(item for item in big.items if chosen(item, "scene") == ["room"]
                and chosen(item, "framing"))
    assert item.prompt.startswith("1girl, solo")
    assert item.prompt.index("bedroom") > item.prompt.index("1girl")


def test_none_records_and_is_filterable(big):
    nones = [item for item in big.items if chosen(item, "shoes") == ["none"]]
    assert nones
    assert all(any(d["label"] == "shoes：无" for d in item.draws) for item in nones)


def test_quota_partitions_are_exact():
    data = base_recipe()
    data["partitions"][1]["needs"] = []
    data["partitions"][1]["quota"] = True
    data["partitions"][1]["options"][0]["weight"] = 2
    result = sample(DatasetRecipe.model_validate(data), 101, 3)
    counts = Counter(chosen(item, "framing")[0] for item in result.items
                     if chosen(item, "framing"))
    stat = next(p for p in result.stats.partitions if p.partition == "framing")
    total = sum(o.count for o in stat.options) + stat.quota_misses
    assert total == 101
    for option in stat.options:
        assert abs(option.count + 0 - option.target * 101) <= 1 + stat.quota_misses
    assert counts


def test_weighted_shares_converge(recipe):
    result = sample(recipe, 400, 99)
    result2 = sample(recipe, 400, 100)
    counts = Counter()
    for res in (result, result2):
        for item in res.items:
            counts.update(chosen(item, "time"))
    share = counts["night"] / sum(counts.values())
    assert 0.43 < share < 0.57


def test_conditional_weights_shift_shares():
    data = base_recipe()
    expression = data["partitions"][6]
    expression["options"][0]["weight_mods"] = [
        {"when": {"chosen": "view.front"}, "factor": 0},
    ]
    result = sample(DatasetRecipe.model_validate(data), 400, 5)
    for item in result.items:
        if chosen(item, "view") == ["front"]:
            assert chosen(item, "expression") != ["smile"]


def test_removal_of_already_drawn_partition_withdraws_and_refunds():
    data = base_recipe()
    # Eye colour now drawn before expression: closed eyes must withdraw it.
    order = data["draw_order"]
    order.remove("eye-color")
    order.insert(order.index("expression"), "eye-color")
    result = sample(DatasetRecipe.model_validate(data), 300, 11)
    closed = [item for item in result.items if chosen(item, "expression") == ["closed"]]
    assert closed
    for item in closed:
        assert not chosen(item, "eye-color")
        assert any(d["option"] == "-removed" and d["partition"] == "eye-color"
                   for d in item.draws)
        assert not tags_of(item) & {"blue eyes", "red eyes"}
    assert result.stats.warnings


def test_rule_removes_options_and_tags_after_drawing():
    data = base_recipe()
    data["rules"].append({"id": "no-cup-at-night",
                          "when": {"state": "time", "in": ["night"]},
                          "effects": {"remove_options": ["hands.cup"],
                                      "remove_tags": ["hair down"]}})
    result = sample(DatasetRecipe.model_validate(data), 300, 13)
    for item in result.items:
        if chosen(item, "time") == ["night"]:
            assert "cup" not in chosen(item, "hands")
            assert "hair down" not in tags_of(item)


def test_overflow_reported_not_truncated():
    data = base_recipe()
    data["partitions"][0]["options"][0]["tags"] = ", ".join(f"tag{i:03d} x" for i in range(30))
    data["partitions"][0]["options"][0]["effects"] = {
        "content_add": [f"extra{i:03d} long filler words here" for i in range(40)],
    }
    result = sample(DatasetRecipe.model_validate(data), 20, 1)
    assert result.stats.overflow > 0
    assert all(len(item.prompt) <= 1000 for item in result.items)


@pytest.mark.parametrize(("mutate", "path"), [
    (lambda d: d["draw_order"].pop(), "draw_order"),
    (lambda d: d["partitions"][5]["options"][0].update(
        when={"state": "time", "in": ["night"]}), "partitions.hairstyle.options.twintails.when"),
    (lambda d: d["partitions"][6]["options"][0].update(
        when={"chosen": "time.night"}), "partitions.expression.options.smile.when.chosen"),
    (lambda d: d["partitions"][0]["options"][0]["effects"].__setitem__(
        "remove_partitions", ["scene"]) if "effects" in d["partitions"][0]["options"][0]
     else d["partitions"][0]["options"][0].update(effects={"remove_partitions": ["scene"]}),
     "partitions.scene.options.room.effects"),
    (lambda d: d["partitions"][8]["options"][1]["slots"]["color"].update(exclude=["pink"]),
     "partitions.outfit.options.dress.slots.color"),
    (lambda d: d["rules"][0]["effects"].update(hide=["eyes"]), "rules.gentle.effects"),
    (lambda d: d["partitions"][1].update(quota=True), "partitions.framing.quota"),
    (lambda d: d["partitions"][12]["options"].append(none()), "partitions.hands"),
    (lambda d: d["regions"].__setitem__(0, {"id": "person", "parent": "eyes"})
     if "regions" in d else d.update(regions=[
         {"id": "person", "parent": "eyes"}, {"id": "face", "parent": "person"},
         {"id": "eyes", "parent": "face"}, {"id": "upper", "parent": "person"},
         {"id": "lower", "parent": "person"}, {"id": "feet", "parent": "lower"},
         {"id": "hands", "parent": "person"}]), "regions.person"),
    (lambda d: d["partitions"][13]["options"][0].update(tags="day // hidden"),
     "partitions.time.options.day.tags"),
])
def test_validation_errors_name_their_path(mutate, path):
    data = base_recipe()
    mutate(data)
    with pytest.raises(ValidationError) as error:
        DatasetRecipe.model_validate(data)
    assert path in str(error.value)


def test_child_options_require_adult_guards():
    data = base_recipe()
    data["partitions"][3]["options"].append(
        opt("kid", "1girl, solo, child", 1, child=True,
            effects={"set": {"age": "child", "gender": "female"}}),
    )
    data["partitions"][8]["options"].append(opt("swim", "white bikini", 1))
    with pytest.raises(ValidationError, match="age = child"):
        DatasetRecipe.model_validate(data)
    data["partitions"][8]["options"][-1]["when"] = {"not": {"state": "age", "in": ["child"]}}
    recipe = DatasetRecipe.model_validate(data)
    result = sample(recipe, 400, 2)
    kids = [item for item in result.items if "kid" in chosen(item, "subject")]
    assert kids
    for item in kids:
        assert "white bikini" not in tags_of(item)
        assert any(d["option"] == "child" for d in item.draws)
    bad = copy.deepcopy(data)
    bad["partitions"][3]["options"][-1]["effects"] = {"set": {"gender": "female"}}
    with pytest.raises(ValidationError, match="age = child"):
        DatasetRecipe.model_validate(bad)


def test_rename_changes_nothing_but_labels(recipe):
    data = base_recipe()
    for p in data["partitions"]:
        p["label"] = p["label"] + "（改名）"
    renamed = sample(DatasetRecipe.model_validate(data), 60, 4)
    original = sample(recipe, 60, 4)
    assert [i.prompt for i in renamed.items] == [i.prompt for i in original.items]
    assert [[(d["partition"], d["option"]) for d in i.draws] for i in renamed.items] == [
        [(d["partition"], d["option"]) for d in i.draws] for i in original.items]


def test_disabled_options_are_never_drawn():
    data = base_recipe()
    data["partitions"][13]["options"][1]["disabled"] = True
    result = sample(DatasetRecipe.model_validate(data), 100, 8)
    assert all(chosen(item, "time") == ["day"] for item in result.items)


def test_unknown_keys_are_rejected():
    data = base_recipe()
    data["partitions"][0]["probability"] = 50
    with pytest.raises(ValidationError):
        DatasetRecipe.model_validate(data)


@pytest.mark.parametrize(("style", "edits", "expected"), [
    ("artist:abc, detailed eyes, soft lighting", {"remove": ["detailed eyes"]},
     "artist:abc, soft lighting"),
    ("artist:abc, {detailed eyes}, sunlight", {"remove": ["Detailed_Eyes", "sunlight"]},
     "artist:abc, {}"),
    ("1.2::detailed eyes, glossy::, flat color", {"remove": ["detailed eyes"]},
     "1.2::, glossy::, flat color"),
    ("artist:abc", {"add": ["gentle smile"]}, "artist:abc, gentle smile"),
    ("artist:abc, gentle smile", {"add": ["gentle smile"]}, "artist:abc, gentle smile"),
    ("1.3::artist:abc, glossy", {"add": ["gentle smile"]},
     "1.3::artist:abc, glossy ::, gentle smile"),
    ("artist:abc\n// detailed eyes", {"remove": ["detailed eyes"], "add": ["x"]},
     "artist:abc\n// detailed eyes\nx"),
    ("detailed eyes", {"remove": ["detailed eyes"]}, ""),
])
def test_resolve_style(style, edits, expected):
    assert resolve_style(style, edits) == expected


def test_resolve_style_without_edits_is_identity():
    for style in ("a, b", " a ,b\n// c", "1.2::a::"):
        assert resolve_style(style, None) == style
        assert resolve_style(style, {"add": [], "remove": []}) == style


def test_basic_template_is_valid_and_clean():
    from novelai_api.recipe_templates import basic_template

    recipe = basic_template()
    for seed in (1, 2, 3):
        result = sample(recipe, 400, seed)
        assert result.stats.produced == 400 and result.stats.overflow == 0
        assert result.stats.stale_dependency == 0 and not result.stats.warnings
        for p in result.stats.partitions:
            assert "conflict" not in p.skips, p.partition
        for item in result.items:
            tags = tags_of(item)
            if "kimono" in item.prompt:
                assert not tags & {"brown boots", "black boots"}
            if "upper body" in tags or "portrait" in tags:
                assert not any("shoes" in t or "boots" in t or "skirt" in t for t in tags)
            if "no humans" in tags:
                assert "1girl" not in tags and "detailed eyes" in item.style_edits["remove"]
