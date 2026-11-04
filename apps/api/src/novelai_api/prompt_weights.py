"""Remove NovelAI emphasis syntax for providers that read plain text (e.g. GPT image).

Mirrors the training-caption rules in apps/web/src/dataset-export.ts: a numeric group
``w::text::`` keeps ``text`` when ``w > 0`` and is dropped when ``w <= 0`` (NovelAI's
"avoid this"); an unclosed group runs to the end. ``{}``/``[]`` emphasis is removed.
Parentheses stay: they are part of Danbooru tags such as ``watercolor (medium)``.
"""

import re

_NUMBER = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
_GROUP = re.compile(rf"(^|[\s,(\[{{])({_NUMBER})::([\s\S]*?)(?:::|$)")
_STRAY_WEIGHT = re.compile(rf"(^|[\s,(\[{{]){_NUMBER}::")
_TAG_SPLIT = re.compile(r"[,\r\n]+")


def _keep_positive(match: re.Match[str]) -> str:
    lead, weight, body = match.groups()
    return lead + body if float(weight) > 0 else lead


def strip_prompt_weights(text: str) -> str:
    """Plain comma-separated tags without weights, emphasis or negative-weight groups."""
    plain = _GROUP.sub(_keep_positive, text)
    plain = _STRAY_WEIGHT.sub(r"\1", plain).replace("::", "")
    plain = re.sub(r"[{}\[\]]", "", plain)
    return ", ".join(tag.strip() for tag in _TAG_SPLIT.split(plain) if tag.strip())
