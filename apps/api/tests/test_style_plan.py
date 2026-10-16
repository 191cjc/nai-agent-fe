"""Golden backend source/decimal vectors for the supported browser style grammar."""

import pytest
from test_generations import INPUT

from novelai_api.generations import GenerationRequest
from novelai_api.style_plan import (
    ExperimentRange,
    create_style_plan,
    decimal_parts,
    format_decimal,
    parse_prompt_tags,
)


def plan(source: str, ranges: list[dict], *, shared: str = "scene"):
    parameters = GenerationRequest(**{**INPUT, "positive_prompt": shared, "style_prompt": source})
    return create_style_plan(parameters, [ExperimentRange(**item) for item in ranges])


def axis(index=0, minimum="0.9", maximum="1.1", step="0.1"):
    return {"tag_index": index, "min": minimum, "max": maximum, "step": step}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("plain,1.20:: blue, red ::,[legacy],foo\\,bar,literal:,escaped\\:", [
            ("plain", "1.0"), (" blue, red ", "1.2"), ("[legacy]", None),
            ("foo\\,bar", "1.0"), ("literal:", None), ("escaped\\:", "1.0"),
        ]),
        ("1.2::a, 0.7::b:: ::,tail", [("a, 0.7::b:: ", "1.2"), ("tail", "1.0")]),
        ("(a,b),{legacy},[legacy],incomplete1.2::a,b", [
            ("(a,b)", "1.0"), ("{legacy}", None), ("[legacy]", None),
            ("incomplete1.2::a,b", None),
        ]),
        ("a\r\nb\nc", [("a", "1.0"), ("b", "1.0"), ("c", "1.0")]),
        ("a\\ ,b\\", [("a\\ ", "1.0"), ("b\\", None)]),
        ("\ufeffartist:a\ufeff,\u0085x\u0085", [("artist:a", "1.0"), ("\u0085x\u0085", "1.0")]),
        ("bad::scope,a::,next", [("bad::scope,a::", None), ("next", "1.0")]),
        ("2::nested(a,[b,c])::,tail", [("nested(a,[b,c])", "2.0"), ("tail", "1.0")]),
    ],
)
def test_supported_tokenizer_golden_vectors(source: str, expected: list) -> None:
    tags = parse_prompt_tags(source)
    assert [(tag.text, tag.weight) for tag in tags] == expected
    assert all(source[tag.start:tag.end] == tag.source for tag in tags)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+.5", "0.5"), ("-0.000", "0.0"), ("0001.20000", "1.2"),
        ("-000.00100", "-0.001"), ("123456789012345678901234567890.000000000000000001",
                                    "123456789012345678901234567890.000000000000000001"),
    ],
)
def test_exact_decimal_normalization_never_uses_binary_or_context_rounding(
    value: str, expected: str,
) -> None:
    assert format_decimal(*decimal_parts(value)) == expected


def test_duplicate_occurrences_cartesian_order_and_neutral_unwrap() -> None:
    experiment = plan("artist:a,artist:a", [axis(1, "1", "2", "1"), axis(0)])
    assert experiment.total == 6
    assert [experiment.combination(index)[0] for index in range(6)] == [
        "0.9::artist:a::,artist:a", "0.9::artist:a::,2.0::artist:a::",
        "artist:a,artist:a", "artist:a,2.0::artist:a::",
        "1.1::artist:a::,artist:a", "1.1::artist:a::,2.0::artist:a::",
    ]
    weights = experiment.combination(3)[1]
    assert [(weight.tag_index, weight.label, weight.weight) for weight in weights] == [
        (0, "artist:a", "1.0"), (1, "artist:a", "2.0"),
    ]


def test_unicode_before_selected_occurrence_and_nested_neutral_source_preservation() -> None:
    source = "😀,  1.2:: blue\\,red, 0.7::nested:: :: , untouched\\: "
    experiment = plan(source, [axis(1, "1", "1", "0.1")])
    assert experiment.combination(0)[0] == "😀,   blue\\,red, 0.7::nested::  , untouched\\: "
    assert experiment.combination(0)[1][0].label == " blue\\,red, 0.7::nested:: "


def test_grid_off_max_negative_cross_zero_and_high_precision() -> None:
    experiment = plan("artist:a", [axis(0, "-0.1", "0.21", "0.1")])
    assert experiment.total == 4
    assert [experiment.combination(index)[1][0].weight for index in range(4)] == [
        "-0.1", "0.0", "0.1", "0.2",
    ]
    assert [experiment.combination(index)[0] for index in range(4)] == [
        "-0.1::artist:a::", "", "0.1::artist:a::", "0.2::artist:a::",
    ]
    precise = plan("artist:a", [axis(
        0, "1.00000000000000000000000000000000001",
        "1.00000000000000000000000000000000003", "0.00000000000000000000000000000000001",
    )])
    assert precise.total == 3
    assert precise.combination(1)[1][0].weight == "1.00000000000000000000000000000000002"


@pytest.mark.parametrize(
    ("source", "removed", "expected"),
    [
        ("  a, b, c  ", [0], "  b, c  "),
        ("  a, b, c  ", [1], "  a, c  "),
        ("  a, b, c  ", [2], "  a, b  "),
        ("  a, b, c  ", [0, 1], "  c  "),
        ("  a, b, c  ", [1, 2], "  a  "),
        ("  a, b, c  ", [0, 2], "  b  "),
        ("  a, b, c  ", [0, 1, 2], ""),
        ("a, a, a", [1], "a, a"),
        ("a\r\n b,\n\n c\r d", [1, 2], "a\r\n d"),
        ("a,, \n b,,c", [1], "a,, \n c"),
        ("foo\\,bar, (a,b), tail", [0], "(a,b), tail"),
        ("foo\\,bar, (a,b), tail", [1], "foo\\,bar, tail"),
        ("2::nested(a,[b,c]), 0.7::d:: ::,tail", [0], "tail"),
        ("😀,2::画风,0.7::乙:: ::,尾", [1], "😀,尾"),
        ("a,[legacy],b", [0, 2], "[legacy]"),
        (" a\\ , b, c\\ ", [1], " a\\ , c\\ "),
    ],
)
def test_zero_omits_selected_occurrences_and_safe_separator_runs(
    source: str, removed: list[int], expected: str,
) -> None:
    experiment = plan(source, [axis(index, "-0.000", "+0", "0.1") for index in removed])
    rendered, weights = experiment.combination(0)
    assert rendered == expected
    assert experiment.max_style_length == len(expected)
    assert [(weight.tag_index, weight.weight) for weight in weights] == [
        (index, "0.0") for index in sorted(removed)
    ]


def test_zero_omissions_do_not_shift_other_selected_source_spans() -> None:
    experiment = plan("  a, 2:: blue,red ::, c, tail  ", [
        axis(0, "0", "0", "1"), axis(1, "1", "2", "1"),
        axis(2, "0", "0", "1"), axis(3, "1.1", "1.1", "1"),
    ])
    assert experiment.total == 2
    assert [experiment.combination(index)[0] for index in range(2)] == [
        "   blue,red , 1.1::tail::  ", "  2.0:: blue,red ::, 1.1::tail::  ",
    ]
    assert [weight.label for weight in experiment.combination(0)[1]] == [
        "a", " blue,red ", "c", "tail",
    ]


def test_zero_is_exact_not_an_epsilon_and_off_grid_zero_is_unreachable() -> None:
    tiny = "0." + "0" * 50 + "1"
    experiment = plan("a", [axis(0, f"-{tiny}", tiny, tiny)])
    assert [experiment.combination(index)[0] for index in range(3)] == [
        f"-{tiny}::a::", "", f"{tiny}::a::",
    ]
    off_grid = plan("a", [axis(0, "-0.1", "0.2", "0.2")], shared="")
    assert [off_grid.combination(index)[0] for index in range(2)] == [
        "-0.1::a::", "0.1::a::",
    ]


@pytest.mark.parametrize("shared", ["", " \t\n"])
def test_any_all_zero_combination_requires_shared_base_before_acceptance(shared: str) -> None:
    with pytest.raises(ValueError, match="Zero weights can remove all style tags"):
        plan("a,b", [axis(0, "-0.1", "0.1", "0.1"), axis(1, "0", "1", "1")],
             shared=shared)
    # An unselected occurrence or an axis that cannot reach zero keeps a base.
    assert plan("a,b", [axis(0, "0", "0", "1")], shared="").combination(0)[0] == "b"
    assert plan("a,b", [axis(0, "0", "1", "1"), axis(1, "1", "1", "1")],
                shared="").combination(0)[0] == "b"


def test_zero_only_bounds_omit_separators_and_preserve_shared_only_composition() -> None:
    experiment = plan(" \ta, b \n", [axis(0, "0", "0.01", "1"), axis(1, "0", "0", "1")],
                      shared=" y ")
    assert experiment.total == 1 and experiment.max_style_length == 0
    rendered, weights = experiment.combination(0)
    assert rendered == "" and len(weights) == 2
    parameters = GenerationRequest(**{**INPUT, "positive_prompt": " y ", "style_prompt": rendered})
    assert parameters.base_prompt == " y "
    near_limit = plan("a", [axis(0, "0", "0", "1")], shared="y" * 2997)
    assert near_limit.max_style_length == 0
    source = "x" * 2980 + ", drop"
    shrunk = plan(source, [axis(), axis(1, "0", "0", "1")], shared="y" * 10)
    assert shrunk.max_style_length == 2987
    assert all(len(GenerationRequest(**{
        **INPUT, "positive_prompt": "y" * 10, "style_prompt": shrunk.combination(index)[0],
    }).base_prompt) <= 3000 for index in range(shrunk.total))


def test_legacy_plan_preserves_zero_emphasis_and_accepts_style_only_zero() -> None:
    parameters = GenerationRequest(**{**INPUT, "positive_prompt": "", "style_prompt": "a"})
    legacy = create_style_plan(parameters, [ExperimentRange(**axis(0, "0", "0", "1"))],
                               plan_version=1)
    assert legacy.combination(0)[0] == "0.0::a::"
    assert legacy.combination(0)[1][0].weight == "0.0"
    assert legacy.max_style_length == 8


def test_neutral_only_off_grid_max_shrinks_near_limit_wrapper() -> None:
    body = "x" * 2990
    experiment = plan(f"2.0::{body}::", [axis(0, "1", "1.01", "0.1")], shared="y")
    assert experiment.total == 1
    assert experiment.max_style_length == 2990
    assert experiment.combination(0)[0] == body


def test_combined_prompt_limit_trims_preserved_outer_style_whitespace() -> None:
    experiment = plan(" " + "x" * 2990 + " ", [axis()], shared="y")
    assert experiment.max_style_length == 2999
    for index in range(experiment.total):
        source, _weights = experiment.combination(index)
        parameters = GenerationRequest(**{
            **INPUT, "positive_prompt": "y", "style_prompt": source,
        })
        assert len(parameters.base_prompt) <= 3000
        assert source.startswith(" ") and source.endswith(" ")
    assert len(GenerationRequest(**{
        **INPUT, "positive_prompt": "y", "style_prompt": experiment.combination(0)[0],
    }).base_prompt) == 3000
    with pytest.raises(ValueError, match="Experiment prompt exceeds limit"):
        plan(" " + "x" * 2991 + " ", [axis()], shared="y")


def test_neutral_unwrap_keeps_raw_limit_and_combined_trim_separate() -> None:
    body = "x" * 2973
    source = " " * 10 + f"2.0::{body}::" + " " * 10
    experiment = plan(source, [axis(0, "1", "1", "0.1")], shared="y" * 18)
    assert len(source) == 3000
    assert experiment.max_style_length == 2993
    rendered, _weights = experiment.combination(0)
    parameters = GenerationRequest(**{
        **INPUT, "positive_prompt": "y" * 18, "style_prompt": rendered,
    })
    assert len(parameters.base_prompt) == 2993
    with pytest.raises(ValueError):
        plan(" " * 4 + "x" * 2990 + " " * 4, [axis()], shared="")


def test_huge_product_stays_lazy_and_exact() -> None:
    experiment = plan(
        ",".join(["x"] * 10), [axis(index, "0", "9" * 90, "1") for index in range(10)],
    )
    assert experiment.total == 10**900
    assert experiment.combination(0)[1][0].weight == "0.0"
    assert experiment.combination(experiment.total - 1)[1][-1].weight == "9" * 90 + ".0"


@pytest.mark.parametrize(
    ("source", "ranges"),
    [
        ("a", []), ("a", [axis(1)]), ("a", [axis(), axis()]),
        ("[legacy]", [axis()]), ("1.1::incomplete", [axis()]), ("literal:", [axis()]),
        ("a", [axis(step="0")]), ("a", [axis(step="-0.1")]),
        ("a", [axis(minimum="2", maximum="1")]), ("a", [axis(minimum="NaN")]),
        ("a", [axis(step="1e-2")]), ("a", [axis(minimum="０.１")]),
        ("a", [axis(minimum="1" * 100, maximum="1" * 100)]),
        (",".join(["x"] * 11), [axis(index, "0", "9" * 97, "1") for index in range(11)]),
        ("a" * 2990, [axis()]),
    ],
)
def test_invalid_or_oversized_entire_plan_is_rejected_before_generation(
    source: str, ranges: list[dict],
) -> None:
    with pytest.raises(ValueError):
        plan(source, ranges)
