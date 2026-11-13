"""Approved default recipe contracts, using only repository-owned synthetic vocabulary."""

from collections import Counter

import pytest

from novelai_api.generations import DatasetItem
from novelai_api.prompt_weights import strip_prompt_weights
from novelai_api.recipe_engine import resolve_style, sample, tag_key
from novelai_api.recipe_templates import (
    BANGS,
    BODY_TAGS,
    EAR_TAGS,
    EYE_TAGS,
    FOREHEAD_TAGS,
    GAZE_TAGS,
    HAIR_COLORS,
    HORN_TAGS,
    SHOE_TAGS,
    basic_template,
)


@pytest.fixture(scope="module")
def recipe():
    return basic_template()


@pytest.fixture(scope="module")
def batch(recipe):
    return sample(recipe, 400, 123)


def choices(item):
    return {draw["partition"]: draw["option"] for draw in item.draws
            if not draw["option"].startswith("-")}


def counts(batch, partition):
    return Counter(selected[partition] for item in batch.items
                   if partition in (selected := choices(item)))


def plain_tags(text):
    return {tag_key(tag) for tag in strip_prompt_weights(text).split(",") if tag.strip()}


def test_default_exact_action_hair_skin_and_fantasy_quotas(batch):
    assert counts(batch, "subject") == {"woman": 400}
    assert counts(batch, "pose-group") == {
        "yoga": 175, "combat": 105, "ordinary": 50, "lying": 20, "fold": 30, "ground": 20,
    }
    assert counts(batch, "fantasy") == {"none": 320, "long-ears": 40, "demon-horns": 40}
    assert counts(batch, "skin") == {"none": 360, "dark": 40}
    hair = counts(batch, "hair-color")
    assert len(hair) == 8 and set(hair.values()) == {50}
    styles = counts(batch, "hairstyle")
    assert len(styles) == 15 and max(styles.values()) - min(styles.values()) == 1
    bangs = counts(batch, "bangs")
    assert len(bangs) == 10 and max(bangs.values()) - min(bangs.values()) <= 1


def test_default_emphasis_is_independent_from_sampling_probability(batch):
    focused = 0
    for item in batch.items:
        selected = choices(item)
        hair = selected["hair-color"]
        if hair in {"white", "black"}:
            assert f"{hair} hair" in item.prompt
            assert f"3::{hair} hair::" not in item.prompt
        else:
            color = {"dark-blue": "dark blue", "light-blue": "light blue",
                     "blonde": "blonde"}.get(hair, hair)
            assert f"3::{color} hair::" in item.prompt
        if "bangs" in selected:
            bang = next(tag for id, _label, tag in BANGS if id == selected["bangs"])
            assert f"6::{bang}::" in item.prompt
        for tag in item.prompt.split(","):
            key = tag_key(tag)
            if "focus" in key.split():
                assert tag.strip() == f"3::{key}::"
                focused += 1
        assert "1boy" not in plain_tags(item.prompt)
        assert "no humans" not in plain_tags(item.prompt)
    assert focused


def test_default_barefoot_is_seventy_percent_of_visible_feet(batch):
    status = counts(batch, "footwear-status")
    assert abs(status["barefoot"] - sum(status.values()) * 0.7) <= 0.5
    assert sum(status.values()) < 400  # cropped ordinary views are excluded
    for item in batch.items:
        selected = choices(item)
        tags = plain_tags(item.prompt)
        if "footwear-status" not in selected:
            assert not {"footwear-status", "shoes", "legwear"} & selected.keys()
            assert "barefoot" not in tags
        elif selected["footwear-status"] == "barefoot":
            assert "barefoot" in tags
            assert "shoes" not in selected and "legwear" not in selected
        else:
            assert "barefoot" not in tags and "shoes" in selected


def test_default_clothing_and_color_relationships(batch):
    for item in batch.items:
        selected = choices(item)
        family = selected.get("outfit-family")
        if selected.get("outfit") == "china-dress":
            outfit = next(d for d in item.draws if d["partition"] == "outfit")
            assert outfit["values"]["color"] != "green"
        if "bottom" in selected:
            if family in {"school", "cheer"}:
                assert selected["bottom"] == "pleated-skirt"
            else:
                assert family == "arabian"
                assert selected["bottom"] in {"pelvic-curtain", "harem-pants"}
            top = next(d for d in item.draws if d["partition"] == "outfit")
            bottom = next(d for d in item.draws if d["partition"] == "bottom")
            assert top["values"]["color"] != bottom["values"]["color"]
        if family == "kimono":
            assert "bottom" not in selected and "legwear" not in selected
            if "shoes" in selected:
                assert selected["shoes"] == "geta"
        if selected.get("fantasy") == "demon-horns":
            assert selected.get("accessory") != "beret"


def test_default_closed_eyes_remove_weighted_eye_details_but_keep_visible_face(batch):
    eye_style = ", ".join(f"3::{tag}::" for tag in [*EYE_TAGS, *GAZE_TAGS])
    style = f"artist:synthetic, {eye_style}, eyelashes, eyebrows, glasses"
    closed = [item for item in batch.items
              if choices(item).get("expression") == "closed-eyes"]
    assert closed
    for item in closed:
        selected = choices(item)
        assert "eye-color" not in selected and "gaze" not in selected
        assert "closed eyes" in plain_tags(item.prompt)
        assert not plain_tags(item.prompt) & set(EYE_TAGS + GAZE_TAGS)
        result = plain_tags(resolve_style(style, item.style_edits))
        assert not result & set(EYE_TAGS + GAZE_TAGS)
        assert {"artist:synthetic", "eyelashes", "eyebrows", "glasses"} <= result
        assert "closed eyes" not in item.style_edits["remove"]
        assert "hair between eyes" not in item.style_edits["remove"]


def test_default_back_views_keep_fantasy_and_hair_but_remove_face_details(batch):
    back_traits = Counter()
    for item in batch.items:
        selected = choices(item)
        if not selected["direction"].startswith("back"):
            continue
        tags = plain_tags(item.prompt)
        assert not {"bangs", "expression", "eye-color", "gaze"} & selected.keys()
        assert "face focus" not in tags
        assert "hairstyle" in selected and "hair-color" in selected
        if selected["fantasy"] == "long-ears":
            assert {"pointy ears", "long ears"} <= tags
            back_traits["ears"] += 1
        if selected["fantasy"] == "demon-horns":
            assert "demon horns" in tags
            back_traits["horns"] += 1
    assert back_traits["ears"] and back_traits["horns"]


def test_default_complex_poses_and_scene_conditions(batch):
    for item in batch.items:
        selected = choices(item)
        tags = plain_tags(item.prompt)
        if selected["pose-group"] != "ordinary":
            assert selected["framing"] == "full-body"
            assert {"full body", "hands and feet in frame"} <= tags
            assert "hands" not in selected
        if selected["pose-group"] in {"lying", "fold", "ground"}:
            assert item.shape == "landscape"
        if selected.get("expression") not in {None, "laughing", "surprised"}:
            assert "closed mouth" in tags and "open mouth" not in tags
            assert "open mouth" in item.style_edits["remove"]
        if selected.get("time") == "night":
            assert "sunlight" in item.style_edits["remove"]
        if selected["scene"] == "simple":
            assert "time" not in selected and "weather" not in selected
        if selected["scene"] in {"classroom", "library", "cafe", "studio"}:
            assert "weather" not in selected


def test_default_items_fit_run_and_editor_limits(batch):
    assert len(batch.items) == 400
    assert batch.stats.overflow == batch.stats.stale_dependency == 0
    assert batch.stats.warnings == []
    assert all(part.quota_misses == 0 for part in batch.stats.partitions)
    for item in batch.items:
        DatasetItem(id=item.id, prompt=item.prompt, draws=item.draws, style_edits=item.style_edits)
        assert len(item.prompt) <= 1000
        assert len(item.draws) <= 128
        assert len(item.style_edits["remove"]) <= 128


def test_default_small_batches_are_deterministic_and_valid(recipe):
    for n in (1, 7, 31):
        first = sample(recipe, n, 987)
        assert first == sample(recipe, n, 987)
        assert len(first.items) == n
        for item in first.items:
            DatasetItem(id=item.id, prompt=item.prompt, draws=item.draws,
                        style_edits=item.style_edits)


def test_default_footwear_cleanup_covers_colored_weighted_style_tags(batch):
    style = "artist:synthetic, " + ", ".join(f"3::{tag}::" for tag in SHOE_TAGS)
    for item in batch.items:
        selected = choices(item)
        if selected.get("footwear-status") == "barefoot":
            assert not plain_tags(resolve_style(style, item.style_edits)) & set(SHOE_TAGS)
        if "footwear-status" not in selected:
            result = plain_tags(resolve_style(style + ", barefoot, toes", item.style_edits))
            assert not result & {*SHOE_TAGS, "barefoot", "toes"}


def test_default_fantasy_quota_cannot_be_overridden_by_baseline_style(batch):
    style = "artist:synthetic, " + ", ".join([*EAR_TAGS, *HORN_TAGS])
    ordinary = ears = horns = 0
    for item in batch.items:
        selected = choices(item)
        tags = plain_tags(resolve_style(style, item.style_edits))
        if selected["fantasy"] == "none":
            assert not tags & set(EAR_TAGS + HORN_TAGS)
            ordinary += 1
        elif selected["fantasy"] == "long-ears":
            assert not tags & set(HORN_TAGS)
            assert set(EAR_TAGS) <= tags
            ears += 1
        else:
            assert not tags & set(EAR_TAGS)
            assert set(HORN_TAGS) <= tags
            horns += 1
    assert (ordinary, ears, horns) == (320, 40, 40)


def test_default_skin_and_hair_choices_override_conflicting_baseline_style(batch):
    style = "artist:synthetic, dark skin, dark-skinned female, " + ", ".join(
        f"3::{tag}::" for _id, tag, _label in HAIR_COLORS
    )
    hair_tags = {tag for _id, tag, _label in HAIR_COLORS}
    for item in batch.items:
        selected = choices(item)
        result = plain_tags(resolve_style(style, item.style_edits))
        hair = next(tag for id, tag, _label in HAIR_COLORS if id == selected["hair-color"])
        assert result & hair_tags == {hair}
        if selected["skin"] == "none":
            assert not result & {"dark skin", "dark-skinned female"}
        else:
            assert {"dark skin", "dark-skinned female"} <= result


def test_default_new_pose_bundles_preserve_support_and_group_distribution(batch):
    expected = {
        "child-pose": ("yoga", {"kneeling", "forehead on floor", "arms extended forward"}),
        "extended-puppy": ("yoga", {"knees under hips", "chest lowered", "palms on floor"}),
        "dolphin": ("yoga", {"forearms on floor", "hips raised", "feet grounded"}),
        "one-legged-downward-dog": (
            "yoga", {"one foot grounded", "other leg extended upward", "palms on floor"},
        ),
        "cat": ("yoga", {"all fours", "back rounded upward", "chin tucked"}),
        "cow": ("yoga", {"all fours", "back arched downward", "head raised"}),
        "reverse-plank": ("ground", {"heels grounded", "arms straight", "hips raised"}),
    }
    seen = set()
    group_poses = {}
    for item in batch.items:
        selected = choices(item)
        group_poses.setdefault(selected["pose-group"], Counter())[selected["pose"]] += 1
        if selected["pose"] not in expected:
            continue
        seen.add(selected["pose"])
        group, support = expected[selected["pose"]]
        assert selected["pose-group"] == group
        assert support | {"full body", "hands and feet in frame"} <= plain_tags(item.prompt)
        assert "hands" not in selected
        if selected["pose"] == "child-pose":
            assert not {
                "bangs", "expression", "eye-color", "gaze", "forehead-mark",
            } & selected.keys()
    assert seen == expected.keys()
    assert len(group_poses["yoga"]) == 15 and sum(group_poses["yoga"].values()) == 175
    assert len(group_poses["ground"]) == 6 and sum(group_poses["ground"].values()) == 20
    for group in ("yoga", "ground"):
        values = group_poses[group].values()
        assert max(values) - min(values) <= 1


def test_default_downward_dog_uses_the_complete_operator_action_bundle(batch):
    matching = [item for item in batch.items if choices(item)["pose"] == "downward-dog"]
    assert matching
    required = {
        "downward-facing dog pose", "hips raised", "hands and feet grounded", "palms spread",
        "spine lengthened", "legs straight", "full body", "hands and feet in frame",
    }
    for item in matching:
        assert required <= plain_tags(item.prompt)


def test_default_adult_body_type_is_conditional_and_cleans_conflicting_style(recipe, batch):
    expected = {
        "large-breasts": ("large breasts", 80),
        "medium-breasts": ("medium breasts", 10),
        "small-breasts": ("small breasts", 10),
    }
    assert {option.id: option.weight for option in recipe.partition("body-type").options} == {
        id: weight for id, (_tag, weight) in expected.items()
    }
    body = counts(batch, "body-type")
    assert body.keys() == expected.keys()
    for id, (_tag, weight) in expected.items():
        assert abs(body[id] - sum(body.values()) * weight / 100) < 1
    assert sum(body.values()) < 400
    style = "artist:synthetic, " + ", ".join(f"3::{tag}::" for tag in BODY_TAGS)
    cropped = set()
    for item in batch.items:
        selected = choices(item)
        tags = plain_tags(item.prompt)
        resolved = plain_tags(resolve_style(style, item.style_edits))
        assert "adult woman" in tags
        if "body-type" not in selected:
            assert not tags & set(BODY_TAGS)
            assert not resolved & set(BODY_TAGS)
            cropped.add(selected["framing"])
        else:
            tag = expected[selected["body-type"]][0]
            assert tags & set(BODY_TAGS) == {tag}
            assert resolved & set(BODY_TAGS) == {tag}
    assert "close-up" in cropped
    unspecified = recipe.model_copy(deep=True)
    unspecified.partition("subject").options[0].effects.set["age"] = "unspecified"
    assert all("body-type" not in choices(item) for item in sample(unspecified, 20, 10).items)


def test_default_forehead_marks_require_visible_uncovered_forehead(batch):
    marks = counts(batch, "forehead-mark")
    assert abs(marks["red-mark"] - sum(marks.values()) * 0.1) <= 0.5
    style = "artist:synthetic, " + ", ".join(f"3::{tag}::" for tag in FOREHEAD_TAGS)
    hidden_reasons = set()
    for item in batch.items:
        selected = choices(item)
        tags = plain_tags(item.prompt)
        resolved = plain_tags(resolve_style(style, item.style_edits))
        mark = selected.get("forehead-mark")
        if mark is not None:
            assert selected["bangs"] in {"parted", "double-parted"}
            assert selected.get("accessory") != "beret"
        if mark == "red-mark":
            assert {"forehead mark", "red forehead markings"} <= tags
        else:
            assert not (tags | resolved) & set(FOREHEAD_TAGS)
            if selected.get("accessory") == "beret":
                hidden_reasons.add("hat")
            if selected.get("bangs") not in {None, "parted", "double-parted"}:
                hidden_reasons.add("bangs")
            if selected["direction"].startswith("back"):
                hidden_reasons.add("back")
            if selected["pose"] == "child-pose":
                hidden_reasons.add("face-down")
    assert hidden_reasons == {"hat", "bangs", "back", "face-down"}


def test_default_relaxed_expression_and_short_wavy_hair_keep_separate_weights(batch):
    relaxed = short_wavy = 0
    for item in batch.items:
        selected = choices(item)
        tags = plain_tags(item.prompt)
        if selected.get("expression") == "relaxed":
            relaxed += 1
            assert {"relaxed expression", "closed mouth"} <= tags
            if selected["framing"] != "wide-shot":
                assert "eye-color" in selected
            assert "open mouth" in item.style_edits["remove"]
        if selected["hairstyle"] == "short-wavy":
            short_wavy += 1
            assert {"short hair", "wavy hair"} <= tags
            assert "6::short hair" not in item.prompt and "6::wavy hair" not in item.prompt
    assert relaxed and short_wavy
    direction_counts = counts(batch, "direction")
    assert len(direction_counts) == 8 and set(direction_counts.values()) == {50}
    for item in batch.items:
        if choices(item)["direction"] in {"back-left", "back-right"}:
            assert "rear three-quarter view" in plain_tags(item.prompt)


def test_default_profile_views_clean_both_eye_details_even_with_uncovered_bangs(batch):
    profiles = 0
    for item in batch.items:
        selected = choices(item)
        resolved = plain_tags(resolve_style(
            "artist:synthetic, 3::heterochromia::, relaxed expression", item.style_edits,
        ))
        if selected["direction"] in {"left", "right"}:
            profiles += 1
            assert "heterochromia" not in plain_tags(item.prompt) | resolved
        if selected["direction"].startswith("back") or selected["pose"] == "child-pose":
            assert "relaxed expression" not in resolved
    assert profiles == 100
