"""Explicit editor line comments; this syntax never reaches an image provider."""

import re
from collections.abc import Iterator

_LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n|$)")


def prompt_lines(source: str) -> Iterator[tuple[int, int, bool]]:
    """Yield physical raw spans, sharing the browser's CRLF/CR/LF definition."""
    for match in _LINE.finditer(source):
        if match.start() == match.end():
            continue
        yield match.start(), match.end(), match.group().lstrip(" \t").startswith("//")


def compile_prompt_comments(source: str) -> str:
    """Drop complete comment lines and retain all surviving source verbatim."""
    return "".join(source[start:end] for start, end, hidden in prompt_lines(source) if not hidden)
