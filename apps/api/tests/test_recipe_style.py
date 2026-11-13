"""Weighted recipe edits use synthetic strings only, including queue normalization."""

import pytest
from pydantic import ValidationError

from novelai_api.generations import DatasetItem
from novelai_api.recipe_engine import Effects, resolve_style
from novelai_api.recipe_style import StyleEdits, normalize_style_tags, style_tag_key


@pytest.mark.parametrize(("values", "expected"), [
    (["3::artist:synthetic, watercolor::"],
     ["3::artist:synthetic::", "3::watercolor::"]),
    (["3::artist:synthetic", "watercolor::"],
     ["3::artist:synthetic::", "3::watercolor::"]),
    (["{a, [b, c]}"], ["{a}", "{[b]}", "{[c]}"]),
    (["3:: 2::a, b::::"], ["3:: 2::a::::", "3::2::b::::"]),
    (["0::a::", "-1.25::b::", "+.5::c::"],
     ["0::a::", "-1.25::b::", "+.5::c::"]),
    (["3::a, b"], ["3::a::", "3::b::"]),
    (["{a，b"], ["{a}", "{b}"]),
    (["a，3::b，c::"], ["a", "3::b::", "3::c::"]),
    (["paint (a,b), x\\,y"], ["paint (a,b)", "x\\,y"]),
    (["a,, b, {}"], ["a", "b"]),
])
def test_normalized_weighted_edits_round_trip_across_recipe_and_queue(values, expected):
    edits = StyleEdits(add=values)
    assert edits.add == expected
    assert normalize_style_tags(edits.add) == expected
    assert Effects(style_add=values).style_add == expected
    item = DatasetItem(id="synthetic", prompt="1girl", style_edits=edits)
    assert DatasetItem.model_validate(item.model_dump()).style_edits == edits


@pytest.mark.parametrize("tag", [
    "3::Blue_Eyes::", "0::Blue_Eyes::", "-1::Blue_Eyes::",
    "3::2::Blue_Eyes::::", "{[Blue_Eyes]}",
])
def test_selectors_keep_zero_negative_and_nested_weight_names(tag):
    assert style_tag_key(tag) == "blue eyes"
    assert StyleEdits(remove=[tag]).remove == ["Blue_Eyes"]
    resolved = resolve_style(f"artist:synthetic, {tag}", {"remove": [tag]})
    assert "Blue_Eyes" not in resolved
    assert "artist:synthetic" in resolved


@pytest.mark.parametrize("field,limit", [("add", 32), ("remove", 128)])
def test_limits_apply_to_normalized_atoms(field, limit):
    values = [", ".join(f"tag-{i}" for i in range(limit))]
    assert len(getattr(StyleEdits.model_validate({field: values}), field)) == limit
    values[0] += ", overflow"
    with pytest.raises(ValidationError):
        StyleEdits.model_validate({field: values})
    assert getattr(StyleEdits.model_validate({field: ["x" * 300]}), field) == ["x" * 300]
    with pytest.raises(ValidationError):
        StyleEdits.model_validate({field: ["x" * 301]})


@pytest.mark.parametrize("tags", [[""], [" "], ["a], b"], ["a::"], ["// hidden"], [1]])
def test_invalid_recipe_and_queue_edits_share_rejection(tags):
    with pytest.raises(ValidationError):
        StyleEdits(add=tags)
    with pytest.raises(ValidationError):
        Effects(style_add=tags)


@pytest.mark.parametrize(("base", "suffix"), [
    ("3::artist:synthetic", "::"),
    ("{artist:synthetic", "}"),
    ("[3::artist:synthetic", "::]"),
    ("3::2::artist:synthetic", "::::"),
])
def test_appended_tags_escape_all_existing_groups_and_trailing_comments(base, suffix):
    assert resolve_style(base, {"add": ["3::watercolor::"]}) == (
        f"{base} {suffix}, 3::watercolor::"
    )
    assert resolve_style(f"{base}\n// synthetic hidden", {"add": ["3::watercolor::"]}) == (
        f"{base}\n// synthetic hidden\n{suffix}, 3::watercolor::"
    )


@pytest.mark.parametrize("literal", ["paint (a,b)", "x\\,y"])
def test_removal_and_duplicate_matching_respect_literal_commas(literal):
    assert resolve_style(f"artist:synthetic, {literal}", {"remove": [literal]}) == (
        "artist:synthetic"
    )
    assert resolve_style(literal, {"add": [literal]}) == literal
