"""Source-preserving prompt tags and lazy exact-decimal Cartesian style plans."""

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from .generations import ExperimentContext, ExperimentWeight, GenerationRequest
from .prompt_comments import compile_prompt_comments, prompt_lines

NUMBER = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)$")
PREFIX = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)::")
BRACKETS = {"(": ")", "[": "]", "{": "}"}
SPACE = frozenset("\t\n\v\f\r \u00a0\u1680\u2028\u2029\u202f\u205f\u3000\ufeff")


def _space(character: str) -> bool:
    return character in SPACE or "\u2000" <= character <= "\u200a"


def _trim(value: str) -> str:
    start, end = 0, len(value)
    while start < end and _space(value[start]):
        start += 1
    while end > start and _space(value[end - 1]):
        end -= 1
    return value[start:end]


def decimal_parts(value: str) -> tuple[int, int]:
    if not NUMBER.fullmatch(value):
        raise ValueError("Weight must be an ordinary decimal")
    negative = value.startswith("-")
    whole, _, fraction = value.lstrip("+-").partition(".")
    places = max(1, len(fraction))
    units = int((whole or "0") + fraction.ljust(places, "0"))
    return (-units if negative else units), places


def format_decimal(units: int, places: int) -> str:
    digits = str(abs(units)).rjust(places + 1, "0")
    return f"{'-' if units < 0 else ''}{digits[:-places]}.{digits[-places:].rstrip('0') or '0'}"


def _normalize(value: str) -> tuple[int, int]:
    return decimal_parts(format_decimal(*decimal_parts(_trim(value))))


def _escaped(source: str, index: int) -> bool:
    previous = index - 1
    while previous >= 0 and source[previous] == "\\":
        previous -= 1
    return (index - previous - 1) % 2 == 1


@dataclass
class _Numeric:
    start: int
    prefix_end: int
    weight: str
    end: int = -1
    closed: bool = False


@dataclass(frozen=True)
class PromptTag:
    start: int
    end: int
    source: str
    text: str
    weight: str | None
    weight_end: int | None
    hidden: bool = False
    manual_only: bool = False
    block_start: int = 0
    block_end: int = 0


def _parse_legacy_prompt_tags(source: str) -> list[PromptTag]:
    """Port the browser grammar using Python offsets, selected by occurrence only."""
    tags: list[PromptTag] = []
    scopes: list[tuple[str, _Numeric | None]] = []
    groups: list[_Numeric] = []
    start = 0
    unsafe = False
    legacy = False

    def finish(end: int) -> None:
        nonlocal start, groups, unsafe, legacy
        left, right = start, end
        while left < right and _space(source[left]):
            left += 1
        while right > left and _space(source[right - 1]) and not _escaped(source, right - 1):
            right -= 1
        if left < right:
            raw = source[left:right]
            outer = next((group for group in groups
                          if group.start == left and group.end == right and group.closed), None)
            if (
                not unsafe and not scopes and outer is not None
                and _trim(source[outer.prefix_end:outer.end - 2])
            ):
                tags.append(PromptTag(
                    left, right, raw, source[outer.prefix_end:outer.end - 2],
                    format_decimal(*decimal_parts(outer.weight)), outer.prefix_end - 2,
                ))
            else:
                trailing = raw.endswith(":") and not _escaped(source, right - 1)
                tags.append(PromptTag(
                    left, right, raw, raw,
                    "1.0" if not unsafe and not scopes and not groups and not legacy
                    and not trailing else None, None,
                ))
        start, groups, unsafe, legacy = end + 1, [], False, False

    index = 0
    while index < len(source):
        character = source[index]
        if character == "\\":
            if index + 1 == len(source):
                unsafe = True
            index += 2
            continue
        prefix = PREFIX.match(source, index) if (
            index == 0 or _space(source[index - 1]) or source[index - 1] in ",()[]{}:"
        ) else None
        if prefix is not None:
            numeric = _Numeric(index, prefix.end(), prefix.group()[:-2])
            groups.append(numeric)
            scopes.append(("::", numeric))
            index = prefix.end()
            continue
        if source.startswith("::", index):
            if scopes and scopes[-1][0] == "::":
                _close, numeric = scopes.pop()
                if numeric is not None:
                    numeric.end, numeric.closed = index + 2, True
            else:
                scopes.append(("::", None))
                unsafe = True
            index += 2
            continue
        if character in BRACKETS:
            scopes.append((BRACKETS[character], None))
            if character in "[{":
                legacy = True
        elif character in ")]}":
            if scopes and scopes[-1][0] == character:
                scopes.pop()
            else:
                unsafe = True
        elif character in ",\n\r" and not scopes:
            finish(index)
        index += 1
    finish(len(source))
    return tags


def parse_prompt_tags(source: str, *, prompt_comments: bool = False) -> list[PromptTag]:
    """Keep frozen legacy occurrence indexes; modern indexes also include hidden tags."""
    legacy = _parse_legacy_prompt_tags(source)
    if not prompt_comments:
        return legacy
    lines = list(prompt_lines(source))

    def manual_source() -> list[PromptTag]:
        start, end = 0, len(source)
        while start < end and _space(source[start]):
            start += 1
        while end > start and _space(source[end - 1]) and not _escaped(source, end - 1):
            end -= 1
        raw = source[start:end]
        return [PromptTag(start, end, raw, raw, None, None, manual_only=True)] if raw else []

    # A scope crossing active/comment lines cannot be edited or split reliably.
    for tag in legacy:
        if "\n" in tag.source or "\r" in tag.source:
            modes = {hidden for start, end, hidden in lines
                     if start < tag.end and end > tag.start}
            if len(modes) > 1:
                return manual_source()
    tags: list[PromptTag] = []
    line_index = 0
    while line_index < len(lines):
        first = line_index
        hidden = lines[first][2]
        while line_index + 1 < len(lines) and lines[line_index + 1][2] == hidden:
            line_index += 1
        block_start, block_end = lines[first][0], lines[line_index][1]
        positions: list[int] = []
        for start, end, _hidden in lines[first:line_index + 1]:
            if hidden:
                while source[start] in " \t":
                    start += 1
                start += 2
                if start < end and source[start] == " ":
                    start += 1
            positions.extend(range(start, end))
        virtual = "".join(source[index] for index in positions)
        for tag in _parse_legacy_prompt_tags(virtual):
            start, end = positions[tag.start], positions[tag.end - 1] + 1
            literal_marker = tag.source.lstrip(" \t").startswith("//")
            literal_body = tag.text.lstrip(" \t").startswith("//")
            # Removing a previous tag, or a numeric wrapper, could activate this marker.
            if not hidden and (literal_marker or literal_body):
                return manual_source()
            manual = "\r" in tag.source or "\n" in tag.source or literal_marker
            tags.append(PromptTag(
                start, end, source[start:end], tag.text,
                None if manual else tag.weight,
                positions[tag.weight_end]
                if not hidden and not manual and tag.weight_end is not None else None,
                hidden, manual, block_start, block_end,
            ))
        line_index += 1
    return tags


def set_tag_weight(source: str, tag: PromptTag, weight: str) -> str:
    if (
        tag.weight is None or tag.hidden or tag.manual_only
        or source[tag.start:tag.end] != tag.source
    ):
        raise ValueError("Stale or unsupported style tag")
    if weight == "1.0":
        return (
            source[:tag.start] + source[tag.weight_end + 2:tag.end - 2] + source[tag.end:]
            if tag.weight_end is not None else source
        )
    if tag.weight_end is not None:
        return source[:tag.start] + weight + source[tag.weight_end:]
    return source[:tag.start] + weight + "::" + tag.source + "::" + source[tag.end:]


def _omission_ranges(
    source: str, tags: list[PromptTag], omitted: set[int], *, prompt_comments: bool = False,
) -> list[tuple[int, int]]:
    """Remove adjacent occurrences and their separators without touching survivors."""
    if not omitted:
        return []
    if prompt_comments:
        ranges = []
        blocks = {(tag.block_start, tag.block_end) for tag in tags if not tag.hidden}
        for block_start, block_end in sorted(blocks):
            members = [(index, tag) for index, tag in enumerate(tags)
                       if not tag.hidden and tag.block_start == block_start]
            local_tags = [PromptTag(
                tag.start - block_start, tag.end - block_start, tag.source,
                tag.text, tag.weight, None,
            ) for _index, tag in members]
            local_omitted = {index for index, (original, _tag) in enumerate(members)
                             if original in omitted}
            ranges.extend(
                (block_start + start, block_start + end) for start, end in
                _omission_ranges(source[block_start:block_end], local_tags, local_omitted)
            )
        return ranges
    if len(omitted) == len(tags):
        return [(0, len(source))]
    ranges = []
    index = 0
    while index < len(tags):
        if index not in omitted:
            index += 1
            continue
        first = index
        while index + 1 in omitted:
            index += 1
        if index + 1 < len(tags):
            ranges.append((tags[first].start, tags[index + 1].start))
        else:
            ranges.append((tags[first - 1].end, tags[index].end))
        index += 1
    return ranges


class ExperimentRange(BaseModel):
    tag_index: int = Field(ge=0, le=2999, strict=True)
    min: str = Field(min_length=1, max_length=1000)
    max: str = Field(min_length=1, max_length=1000)
    step: str = Field(min_length=1, max_length=1000)


@dataclass(frozen=True)
class Dimension:
    range: ExperimentRange
    tag: PromptTag
    count: int
    min_units: int
    step_units: int
    places: int


@dataclass(frozen=True)
class StylePlan:
    source: str
    dimensions: tuple[Dimension, ...]
    total: int
    max_style_length: int
    plan_version: Literal[1, 2] = 2
    prompt_comments: bool = False

    def combination(self, index: int) -> tuple[str, list[ExperimentWeight]]:
        if not 0 <= index < self.total:
            raise ValueError("Style combination out of range")
        remaining, source = index, self.source
        weights = []
        omitted: set[int] = set()
        edits: list[tuple[int, int, PromptTag | None, str]] = []
        for dimension in reversed(self.dimensions):
            remaining, value_index = divmod(remaining, dimension.count)
            weight = format_decimal(
                dimension.min_units + value_index * dimension.step_units, dimension.places,
            )
            if self.plan_version == 2 and weight == "0.0":
                omitted.add(dimension.range.tag_index)
            else:
                edits.append((dimension.tag.start, dimension.tag.end, dimension.tag, weight))
            weights.append(ExperimentWeight(
                tag_index=dimension.range.tag_index, label=dimension.tag.text, weight=weight,
            ))
        edits.extend((start, end, None, "") for start, end in _omission_ranges(
            self.source, parse_prompt_tags(self.source, prompt_comments=self.prompt_comments),
            omitted, prompt_comments=self.prompt_comments,
        ))
        for start, end, tag, weight in sorted(edits, key=lambda edit: edit[0], reverse=True):
            source = (
                set_tag_weight(source, tag, weight) if tag is not None
                else source[:start] + source[end:]
            )
        return source, list(reversed(weights))


def create_style_plan(
    parameters: GenerationRequest, ranges: list[ExperimentRange], *,
    plan_version: Literal[1, 2] = 2,
) -> StylePlan:
    if plan_version not in (1, 2):
        raise ValueError("Unsupported style plan version")
    if not 1 <= len(ranges) <= 1500:
        raise ValueError("Select between one and 1500 style tags")
    tags = parse_prompt_tags(parameters.style_prompt, prompt_comments=parameters.prompt_comments)
    selected = set()
    dimensions = []
    for supplied in ranges:
        if (
            supplied.tag_index >= len(tags) or supplied.tag_index in selected
            or tags[supplied.tag_index].weight is None or tags[supplied.tag_index].hidden
        ):
            raise ValueError("Invalid or unsupported style tag selection")
        selected.add(supplied.tag_index)
        tag = tags[supplied.tag_index]
        values = [_normalize(value) for value in (supplied.min, supplied.max, supplied.step)]
        count_places = max(places for _units, places in values)
        minimum, maximum, step = [units * 10 ** (count_places - places)
                                  for units, places in values]
        if step <= 0 or minimum > maximum:
            raise ValueError("Invalid style range")
        places = max(values[0][1], values[2][1])
        min_units = values[0][0] * 10 ** (places - values[0][1])
        step_units = values[2][0] * 10 ** (places - values[2][1])
        normalized = ExperimentRange(
            tag_index=supplied.tag_index, min=format_decimal(min_units, places),
            max=format_decimal(*values[1]), step=format_decimal(step_units, places),
        )
        dimensions.append(Dimension(
            normalized, tag, (maximum - minimum) // step + 1, min_units, step_units, places,
        ))
    dimensions.sort(key=lambda dimension: dimension.tag.start)
    fixed_zeros = {
        dimension.range.tag_index for dimension in dimensions
        if plan_version == 2 and dimension.count == 1 and dimension.min_units == 0
    }
    maximum_length = len(parameters.style_prompt) - sum(
        end - start for start, end in _omission_ranges(
            parameters.style_prompt, tags, fixed_zeros, prompt_comments=parameters.prompt_comments,
        )
    )
    total = 1
    for dimension in dimensions:
        total *= dimension.count
        if len(str(total)) > 1000:
            raise ValueError("Experiment total exceeds metadata limit")
        if dimension.range.tag_index in fixed_zeros:
            continue
        if dimension.count == 1 and dimension.range.min == "1.0":
            maximum_length += len(dimension.tag.text) - len(dimension.tag.source)
            continue
        last = dimension.min_units + (dimension.count - 1) * dimension.step_units
        largest = max(abs(dimension.min_units), abs(last))
        integer_digits = len(str(largest // 10 ** dimension.places))
        weight_length = integer_digits + 1 + dimension.places + (dimension.min_units < 0)
        if weight_length > 100:
            raise ValueError("Experiment weight exceeds metadata limit")
        maximum_length += (
            weight_length - (dimension.tag.weight_end - dimension.tag.start)
            if dimension.tag.weight_end is not None else weight_length + 4
        )
    shared = parameters.effective_positive_prompt.strip()
    can_be_empty = len(dimensions) == len([tag for tag in tags if not tag.hidden]) and all(
        dimension.min_units <= 0
        and -dimension.min_units % dimension.step_units == 0
        and -dimension.min_units // dimension.step_units < dimension.count
        for dimension in dimensions
    )
    if plan_version == 2 and can_be_empty and not shared:
        raise ValueError("Zero weights can remove all style tags; add a shared prompt")
    if parameters.prompt_comments:
        hidden_length = len(parameters.style_prompt) - len(
            compile_prompt_comments(parameters.style_prompt),
        )
        effective_maximum = maximum_length - hidden_length
        combined_length = effective_maximum + (len(shared) + 2 if shared else 0)
        if not effective_maximum:
            combined_length = len(parameters.effective_positive_prompt)
    else:
        outer_space = len(parameters.style_prompt) - len(parameters.style_prompt.strip())
        combined_length = (
            maximum_length - outer_space + (len(shared) + 2 if shared else 0)
            if maximum_length else len(parameters.positive_prompt)
        )
    if maximum_length > 3000 or combined_length > 3000:
        raise ValueError("Experiment prompt exceeds limit")
    plan = StylePlan(
        parameters.style_prompt, tuple(dimensions), total, maximum_length, plan_version,
        parameters.prompt_comments,
    )
    # Validate the exact shared saved-metadata bounds before any accepted run.
    _source, weights = plan.combination(0)
    ExperimentContext(id="00000000-0000-0000-0000-000000000000", ordinal="1",
                      total=str(total), weights=weights)
    return plan
