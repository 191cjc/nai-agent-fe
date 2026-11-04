import pytest

from novelai_api.prompt_weights import strip_prompt_weights


@pytest.mark.parametrize(("source", "expected"), [
    ("6::white hair::, red eyes", "white hair, red eyes"),
    ("1.5::long hair, ribbon::, smile", "long hair, ribbon, smile"),
    ("1girl, -1::hat::, smile", "1girl, smile"),
    ("1girl, 0::glasses::, smile", "1girl, smile"),
    ("{{blue eyes}}, [[freckles]]", "blue eyes, freckles"),
    ("{1.3::white hair::}, -2::text, watermark", "white hair"),
    ("1.2::unclosed tail", "unclosed tail"),
    ("watercolor (medium), 1990s (style)", "watercolor (medium), 1990s (style)"),
    ("3d, 2::blush::", "3d, blush"),
    ("", ""),
])
def test_strip_prompt_weights(source: str, expected: str) -> None:
    assert strip_prompt_weights(source) == expected
