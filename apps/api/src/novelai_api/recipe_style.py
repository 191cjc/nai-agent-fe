"""Shared, bounded recipe style edits with independently balanced emphasis tags."""

import re
from functools import lru_cache
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

MAX_STYLE_ADDITIONS = 32
MAX_STYLE_REMOVALS = 128
MAX_STYLE_TAG = 300
StyleTag = Annotated[str, Field(min_length=1, max_length=MAX_STYLE_TAG)]
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)::")
_WEIGHT = re.compile(r"(^|[\s,，([{]|(?<=::))[+-]?(?:\d+(?:\.\d+)?|\.\d+)::")
_SPACES = re.compile(r"\s+")


@lru_cache(maxsize=65536)
def plain_style_tag(tag: str) -> str:
    """A selector keeps the name even when its numeric emphasis is zero/negative."""
    plain = _WEIGHT.sub(r"\1", tag).replace("::", "")
    return re.sub(r"[{}\[\]]", "", plain).strip()


@lru_cache(maxsize=65536)
def style_tag_key(tag: str) -> str:
    return _SPACES.sub(" ", plain_style_tag(tag).replace("_", " ")).strip().lower()


def _split_style(
    text: str, *, strict: bool = True, raw_pieces: bool = False,
) -> tuple[list[str], str]:
    if strict and "//" in text:
        raise ValueError("Style edits cannot contain comment markers")
    scopes: list[tuple[str, str]] = []
    inherited: list[tuple[str, str]] = []
    piece: list[str] = []
    result: list[str] = []
    parentheses = 0

    def emit() -> None:
        if raw_pieces:
            result.append("".join(piece))
            return
        raw = "".join(piece).strip()
        if not raw:
            return
        tag = "".join(opener for opener, _ in inherited) + raw
        tag += "".join(closer for _, closer in reversed(scopes))
        if style_tag_key(tag):
            result.append(tag)

    index = 0
    while index < len(text):
        character = text[index]
        if character == "\\" and index + 1 < len(text):
            piece.append(text[index:index + 2])
            index += 2
            continue
        match = _NUMBER.match(text, index) if (
            index == 0 or text[index - 1].isspace() or text[index - 1] in ",，([{"
            or text[max(0, index - 2):index] == "::"
        ) else None
        if match:
            piece.append(match.group())
            scopes.append((match.group(), "::"))
            index = match.end()
            continue
        if text.startswith("::", index):
            if not scopes or scopes[-1][1] != "::":
                if strict:
                    raise ValueError("Unmatched numeric emphasis delimiter in style edit")
            else:
                scopes.pop()
            piece.append("::")
            index += 2
            continue
        if character in "{[":
            scopes.append((character, "}" if character == "{" else "]"))
        elif character in "}]":
            if not scopes or scopes[-1][1] != character:
                if strict:
                    raise ValueError("Unmatched emphasis bracket in style edit")
            else:
                scopes.pop()
        elif character == "(":
            parentheses += 1
        elif character == ")":
            parentheses = max(0, parentheses - 1)
        if character in ",，\n\r" and not parentheses:
            emit()
            piece = []
            inherited = list(scopes)
        else:
            piece.append(character)
        index += 1
    emit()
    return result, "".join(closer for _, closer in reversed(scopes))


def split_style_tags(text: str) -> list[str]:
    """Split groups into independently balanced atoms without leaking emphasis.

    ``3::a, b::`` becomes ``3::a::`` / ``3::b::``. Braces, brackets and
    nested groups retain the same scopes. Unclosed groups end at this input's end.
    Parentheses and escaped commas remain literal tag text.
    """
    return list(_split_strict(text))


@lru_cache(maxsize=16384)
def _split_strict(text: str) -> tuple[str, ...]:
    return tuple(_split_style(text)[0])


def unclosed_style_suffix(text: str) -> str:
    """Close existing style groups before additions without revalidating legacy text."""
    return _split_style(text, strict=False)[1]


def split_style_pieces(text: str) -> list[str]:
    """Keep existing style text/markers verbatim while finding literal tag boundaries."""
    return _split_style(text, strict=False, raw_pieces=True)[0]


def normalize_style_tags(values: list[str], *, remove: bool = False) -> list[str]:
    """Join legacy comma-split groups before making independently bounded tags."""
    tags = split_style_tags(", ".join(values))
    normalized = [plain_style_tag(tag) if remove else tag for tag in tags]
    if any(len(tag) > MAX_STYLE_TAG for tag in normalized):
        raise ValueError(f"Style edit tags cannot exceed {MAX_STYLE_TAG} characters")
    return normalized


class StyleEdits(BaseModel):
    """Per-item style additions keep emphasis; removals are plain tag selectors."""

    model_config = ConfigDict(extra="forbid")

    add: list[StyleTag] = Field(default_factory=list, max_length=MAX_STYLE_ADDITIONS)
    remove: list[StyleTag] = Field(default_factory=list, max_length=MAX_STYLE_REMOVALS)

    @field_validator("add", "remove", mode="before")
    @classmethod
    def normalize(cls, value: Any, info: ValidationInfo) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(tag, str) for tag in value):
            raise ValueError("Style edits must be lists of strings")
        if any(not tag.strip() for tag in value):
            raise ValueError("Style edit tags cannot be blank")
        return normalize_style_tags(value, remove=info.field_name == "remove")
