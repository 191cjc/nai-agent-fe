"""Random style-dataset recipes: validated model and a pure, deterministic sampler.

A recipe is a set of user-defined partitions (framing, top, hands, ...) holding weighted
options. Drawing follows ``draw_order``; every drawn option immediately applies its
structural effects (hide regions, set state, consume resources, remove or whitelist other
partitions/options), so later partitions only see what is still possible. After all
partitions, rules run on the complete item. Tag-level effects (content and per-item style
edits) are applied when the prompt is assembled in ``prompt_order``.

Everything is referenced by immutable ids; labels are display text only. The sampler does
no I/O and never calls a provider. See .trellis/spec/backend/dataset-recipe-contract.md.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from .prompt_weights import strip_prompt_weights
from .recipe_style import StyleEdits, split_style_pieces, style_tag_key, unclosed_style_suffix

RECIPE_VERSION = 1
MAX_PROMPT = 1000
MAX_ITEMS = 4000
ID_PATTERN = r"^[a-z0-9][a-z0-9-]*$"
_ID = re.compile(ID_PATTERN)
_PLACEHOLDER = re.compile(r"\{([a-z0-9][a-z0-9-]*)\}")
_SPACES = re.compile(r"\s+")
NONE_ID = "none"
CHILD_STATE = ("age", "child")
# Never combinable with a child subject (also see CHILD_UNSAFE_STYLE in DatasetRun.tsx).
CHILD_UNSAFE = re.compile(
    r"\b(swimsuit|bikini|swimwear|underwear|lingerie|panties|bra|nude|naked|topless|bottomless|"
    r"bed|on bed|bath|bathing|bathtub|onsen|shower|towel|cleavage|breasts?|thighs?|"
    r"thick thighs|wide hips|curvy|sexy|seductive|sensual|erotic|nsfw|lewd|midriff|navel|"
    r"bare shoulders|pantyhose|garter|see-through|wet clothes)\b",
    re.IGNORECASE,
)

Id = Annotated[str, Field(min_length=1, max_length=64, pattern=ID_PATTERN)]
Tag = Annotated[str, Field(min_length=1, max_length=300)]
Label = Annotated[str, Field(max_length=100)]
Condition = dict[str, Any]

@lru_cache(maxsize=65536)
def tag_key(tag: str) -> str:
    """Compare visible tags independently of emphasis, case and underscore spelling."""
    return _SPACES.sub(" ", strip_prompt_weights(tag).replace("_", " ")).strip().lower()

_SEPARATORS = re.compile(r"[,，\r\n]+")

def split_tags(text: str) -> list[str]:
    """Tags split on ASCII/full-width commas and newlines; blanks dropped."""
    return [_SPACES.sub(" ", part).strip() for part in _SEPARATORS.split(text) if part.strip()]

def normalize_prompt(text: str) -> str:
    """Collapse empty tags and stray separators: 'a,, b ,' -> 'a, b'."""
    return ", ".join(split_tags(text))

class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Region(_Model):
    id: Id
    label: Label = ""
    parent: Id | None = None

class SlotValue(_Model):
    id: Id
    tag: Tag
    label: Label = ""
    weight: float = Field(default=1, gt=0, le=1_000_000, allow_inf_nan=False)

class Slot(_Model):
    id: Id
    label: Label = ""
    values: list[SlotValue] = Field(min_length=1, max_length=100)

class SlotUse(_Model):
    exclude: list[Id] = Field(default_factory=list, max_length=100)
    only: list[Id] | None = Field(default=None, max_length=100)
    weight_mods: dict[Id, float] = Field(default_factory=dict)
    # State key receiving the drawn value id (e.g. top_color = red).
    set_state: Id | None = None
    # Value may not equal the current value of this state key (e.g. bottom != top colour).
    exclude_state: Id | None = None

    @field_validator("weight_mods")
    @classmethod
    def finite_factors(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not 0 <= factor <= 1000 for factor in value.values()):
            raise ValueError("Slot weight factors must be between 0 and 1000")
        return value

class WeightMod(_Model):
    when: Condition
    factor: float = Field(ge=0, le=1000, allow_inf_nan=False)

def _tag_list(value: list[str]) -> list[str]:
    tags: list[str] = []
    for text in value:
        tags.extend(tag for tag in split_tags(text) if tag not in tags)
    return tags

class Effects(_Model):
    hide: list[Id] = Field(default_factory=list, max_length=32)
    set: dict[Id, Id] = Field(default_factory=dict)
    consume: dict[Id, int] = Field(default_factory=dict)
    remove_partitions: list[Id] = Field(default_factory=list, max_length=64)
    remove_options: list[str] = Field(default_factory=list, max_length=400)
    allow_options: dict[Id, list[Id]] = Field(default_factory=dict)
    # Key: "partition.option.slot".
    allow_values: dict[str, list[Id]] = Field(default_factory=dict)
    content_add: list[Tag] = Field(default_factory=list, max_length=64)
    remove_tags: list[Tag] = Field(default_factory=list, max_length=64)
    style_add: list[Tag] = Field(default_factory=list, max_length=32)
    style_remove: list[Tag] = Field(default_factory=list, max_length=128)

    @field_validator("content_add", "remove_tags", mode="after")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        return _tag_list(value)

    @field_validator("style_add", "style_remove", mode="before")
    @classmethod
    def clean_style_tags(cls, value: Any, info: ValidationInfo) -> list[str]:
        field = "add" if info.field_name == "style_add" else "remove"
        return getattr(StyleEdits.model_validate({field: value}), field)

    @field_validator("consume")
    @classmethod
    def positive_consume(cls, value: dict[str, int]) -> dict[str, int]:
        if any(not 1 <= amount <= 100 for amount in value.values()):
            raise ValueError("Resource amounts must be between 1 and 100")
        return value

    def structural(self) -> bool:
        return bool(self.hide or self.set or self.remove_partitions or self.remove_options
                    or self.allow_options or self.allow_values)

class Option(_Model):
    id: Id
    label: Label = ""
    tags: str = Field(default="", max_length=300)
    weight: float = Field(default=1, gt=0, le=1_000_000, allow_inf_nan=False)
    weight_mods: list[WeightMod] = Field(default_factory=list, max_length=16)
    when: Condition | None = None
    needs: list[Id] = Field(default_factory=list, max_length=32)
    effects: Effects = Field(default_factory=Effects)
    slots: dict[Id, SlotUse] = Field(default_factory=dict)
    none: bool = False
    child: bool = False
    disabled: bool = False
    size: Literal["portrait", "square", "landscape"] | None = None

class Partition(_Model):
    id: Id
    label: Label = ""
    mode: Literal["one", "fill"] = "one"
    max_draws: int = Field(default=1, ge=1, le=10)
    quota: bool = False
    when: Condition | None = None
    needs: list[Id] = Field(default_factory=list, max_length=32)
    options: list[Option] = Field(min_length=1, max_length=200)

class Rule(_Model):
    id: Id
    label: Label = ""
    when: Condition
    effects: Effects
    disabled: bool = False

class StyleTag(_Model):
    tag: Tag
    needs: Id

DEFAULT_REGIONS = [
    Region(id="person", label="人物"),
    Region(id="face", label="脸", parent="person"),
    Region(id="eyes", label="眼睛", parent="face"),
    Region(id="upper", label="上身", parent="person"),
    Region(id="lower", label="下身", parent="person"),
    Region(id="feet", label="脚", parent="lower"),
    Region(id="hands", label="手", parent="person"),
]

class RecipeError(ValueError):
    """Static recipe error carrying a JSON path."""

    def __init__(self, path: str, message: str):
        super().__init__(f"{path}: {message}")
        self.path = path

class DatasetRecipe(_Model):
    version: Literal[1] = 1
    regions: list[Region] = Field(default_factory=lambda: list(DEFAULT_REGIONS), max_length=32)
    resources: dict[Id, int] = Field(default_factory=dict)
    states: dict[Id, Label] = Field(default_factory=dict)
    slots: list[Slot] = Field(default_factory=list, max_length=20)
    style_tags: list[StyleTag] = Field(default_factory=list, max_length=128)
    glossary: dict[str, str] = Field(default_factory=dict)
    draw_order: list[Id]
    prompt_order: list[Id] | None = None
    partitions: list[Partition] = Field(min_length=1, max_length=40)
    rules: list[Rule] = Field(default_factory=list, max_length=100)

    @field_validator("glossary")
    @classmethod
    def bounded_glossary(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 5000:
            raise ValueError("Glossary holds at most 5000 entries")
        if any(not 0 < len(key) <= 300 or len(gloss) > 100 for key, gloss in value.items()):
            raise ValueError("Glossary entries must be 1-300 chars with glosses up to 100")
        return value

    @field_validator("resources")
    @classmethod
    def bounded_resources(cls, value: dict[str, int]) -> dict[str, int]:
        if len(value) > 32 or any(not 1 <= amount <= 100 for amount in value.values()):
            raise ValueError("At most 32 resources with capacity 1-100")
        return value

    @model_validator(mode="after")
    def valid_recipe(self) -> Self:
        _validate(self)
        return self

    @property
    def output_order(self) -> list[str]:
        return self.prompt_order or self.draw_order

    def partition(self, partition_id: str) -> Partition:
        return next(part for part in self.partitions if part.id == partition_id)

# --------------------------------------------------------------------------- validation

_CONDITION_KEYS = {"all", "any", "not", "chosen", "partition_drawn", "state", "visible", "tag"}

@dataclass
class _Scope:
    """What a draw-time condition may reference: earlier partitions and state keys."""

    partitions: set[str]
    states: set[str]
    rule: bool = False

def _check_condition(
    recipe: DatasetRecipe, condition: Any, path: str, scope: _Scope, depth: int = 0,
    counter: list[int] | None = None,
) -> None:
    counter = counter if counter is not None else [0]
    counter[0] += 1
    if depth > 8 or counter[0] > 64:
        raise RecipeError(path, "condition is too deep or too large (depth 8, 64 nodes)")
    if not isinstance(condition, dict) or not condition:
        raise RecipeError(path, "condition must be an object")
    keys = set(condition)
    head = keys & _CONDITION_KEYS
    if len(head) != 1:
        raise RecipeError(path, f"condition needs exactly one of {sorted(_CONDITION_KEYS)}")
    (kind,) = head
    allowed = {kind, "in"} if kind == "state" else {kind}
    if keys - allowed:
        raise RecipeError(path, f"unknown condition keys {sorted(keys - allowed)}")
    value = condition[kind]
    if kind in ("all", "any"):
        if not isinstance(value, list) or not value:
            raise RecipeError(path, f"'{kind}' needs a non-empty list")
        for index, child in enumerate(value):
            _check_condition(recipe, child, f"{path}.{kind}[{index}]", scope, depth + 1, counter)
    elif kind == "not":
        _check_condition(recipe, value, f"{path}.not", scope, depth + 1, counter)
    elif kind == "chosen":
        partition_id, option_id = _option_ref(recipe, value, f"{path}.chosen")
        del option_id
        if not scope.rule and partition_id not in scope.partitions:
            raise RecipeError(
                f"{path}.chosen", f"'{partition_id}' is drawn later; move it earlier in "
                "draw_order or use a rule",
            )
    elif kind == "partition_drawn":
        if value not in _partition_ids(recipe):
            raise RecipeError(f"{path}.partition_drawn", f"unknown partition '{value}'")
        if not scope.rule and value not in scope.partitions:
            raise RecipeError(
                f"{path}.partition_drawn",
                f"'{value}' is drawn later; move it earlier in draw_order or use a rule",
            )
    elif kind == "state":
        values = condition.get("in")
        if not isinstance(value, str) or not _ID.match(value):
            raise RecipeError(f"{path}.state", "state key must be an id")
        if not isinstance(values, list) or not values or not all(
            isinstance(item, str) and _ID.match(item) for item in values
        ):
            raise RecipeError(f"{path}.in", "state condition needs a non-empty list of value ids")
        if value not in _state_keys(recipe):
            raise RecipeError(f"{path}.state", f"no option sets state '{value}'")
        if not scope.rule and value not in scope.states:
            raise RecipeError(
                f"{path}.state", f"state '{value}' is only set by later partitions",
            )
    elif kind == "visible":
        if value not in _region_ids(recipe):
            raise RecipeError(f"{path}.visible", f"unknown region '{value}'")
    elif kind == "tag":
        if not isinstance(value, str) or not tag_key(value) or len(value) > 300:
            raise RecipeError(f"{path}.tag", "tag must be non-blank text")

def _partition_ids(recipe: DatasetRecipe) -> set[str]:
    return {part.id for part in recipe.partitions}

def _region_ids(recipe: DatasetRecipe) -> set[str]:
    return {region.id for region in recipe.regions}

def _state_keys(recipe: DatasetRecipe) -> set[str]:
    keys: set[str] = set()
    for part in recipe.partitions:
        for option in part.options:
            keys.update(option.effects.set)
            keys.update(use.set_state for use in option.slots.values() if use.set_state)
    return keys

def _option_ref(recipe: DatasetRecipe, value: Any, path: str) -> tuple[str, str]:
    if not isinstance(value, str) or value.count(".") != 1:
        raise RecipeError(path, "option reference must be 'partition.option'")
    partition_id, option_id = value.split(".")
    parts = {part.id: part for part in recipe.partitions}
    if partition_id not in parts:
        raise RecipeError(path, f"unknown partition '{partition_id}'")
    if option_id not in {option.id for option in parts[partition_id].options}:
        raise RecipeError(path, f"unknown option '{option_id}' in '{partition_id}'")
    return partition_id, option_id

def _guards_adult(condition: Condition | None) -> bool:
    """Syntactic check: the condition requires that the subject is not a child."""
    if not condition:
        return False
    if "not" in condition:
        inner = condition["not"]
        return isinstance(inner, dict) and inner.get("state") == CHILD_STATE[0] and (
            CHILD_STATE[1] in (inner.get("in") or [])
        )
    if "state" in condition:
        return condition["state"] == CHILD_STATE[0] and CHILD_STATE[1] not in condition["in"]
    if "all" in condition:
        return any(_guards_adult(child) for child in condition["all"])
    return False

def _effect_refs(
    recipe: DatasetRecipe, effects: Effects, path: str, own_partition: str | None,
    *, rule: bool,
) -> None:
    regions, parts = _region_ids(recipe), {part.id: part for part in recipe.partitions}
    if rule and (effects.hide or effects.set or effects.consume):
        raise RecipeError(path, "rules cannot hide regions, set state or consume resources")
    for region in effects.hide:
        if region not in regions:
            raise RecipeError(f"{path}.hide", f"unknown region '{region}'")
    for resource in effects.consume:
        if resource not in recipe.resources:
            raise RecipeError(f"{path}.consume", f"unknown resource '{resource}'")
    for partition_id in [*effects.remove_partitions, *effects.allow_options]:
        if partition_id not in parts:
            raise RecipeError(path, f"unknown partition '{partition_id}'")
        if partition_id == own_partition:
            raise RecipeError(path, "an option cannot remove or restrict its own partition")
    for index, ref in enumerate(effects.remove_options):
        partition_id, _ = _option_ref(recipe, ref, f"{path}.remove_options[{index}]")
        if partition_id == own_partition:
            raise RecipeError(path, "an option cannot remove options of its own partition")
    for partition_id, option_ids in effects.allow_options.items():
        known = {option.id for option in parts[partition_id].options}
        if not option_ids or set(option_ids) - known:
            raise RecipeError(
                f"{path}.allow_options.{partition_id}", "needs existing option ids",
            )
    for key, value_ids in effects.allow_values.items():
        pieces = key.split(".")
        if len(pieces) != 3:
            raise RecipeError(f"{path}.allow_values", "key must be 'partition.option.slot'")
        partition_id, _ = _option_ref(recipe, ".".join(pieces[:2]), f"{path}.allow_values")
        if partition_id == own_partition:
            raise RecipeError(path, "an option cannot restrict its own partition")
        option = next(o for o in parts[partition_id].options if o.id == pieces[1])
        slot = next((slot for slot in recipe.slots if slot.id == pieces[2]), None)
        if slot is None or pieces[2] not in _placeholders(option.tags):
            raise RecipeError(f"{path}.allow_values.{key}", "option does not use that slot")
        if not value_ids or set(value_ids) - {value.id for value in slot.values}:
            raise RecipeError(f"{path}.allow_values.{key}", "needs existing value ids")

def _placeholders(text: str) -> list[str]:
    return _PLACEHOLDER.findall(text)

def _validate(recipe: DatasetRecipe) -> None:
    parts = recipe.partitions
    ids = [part.id for part in parts]
    if len(set(ids)) != len(ids):
        raise RecipeError("partitions", "duplicate partition id")
    if sorted(recipe.draw_order) != sorted(ids):
        raise RecipeError("draw_order", "must list every partition exactly once")
    if recipe.prompt_order is not None and sorted(recipe.prompt_order) != sorted(ids):
        raise RecipeError("prompt_order", "must list every partition exactly once")
    if sum(len(part.options) for part in parts) > 4000:
        raise RecipeError("partitions", "at most 4000 options in total")
    # Regions: unique, parents exist, no cycles.
    regions = {region.id: region for region in recipe.regions}
    if len(regions) != len(recipe.regions):
        raise RecipeError("regions", "duplicate region id")
    for region in recipe.regions:
        seen, cursor = {region.id}, region.parent
        while cursor is not None:
            if cursor not in regions:
                raise RecipeError(f"regions.{region.id}", f"unknown parent '{cursor}'")
            if cursor in seen:
                raise RecipeError(f"regions.{region.id}", "region parents form a cycle")
            seen.add(cursor)
            cursor = regions[cursor].parent
    slots = {slot.id: slot for slot in recipe.slots}
    if len(slots) != len(recipe.slots):
        raise RecipeError("slots", "duplicate slot id")
    for slot in recipe.slots:
        if len({value.id for value in slot.values}) != len(slot.values):
            raise RecipeError(f"slots.{slot.id}", "duplicate value id")
    for index, style_tag in enumerate(recipe.style_tags):
        if style_tag.needs not in regions:
            raise RecipeError(f"style_tags[{index}].needs", f"unknown region '{style_tag.needs}'")
    if len(recipe.rules) != len({rule.id for rule in recipe.rules}):
        raise RecipeError("rules", "duplicate rule id")

    has_child = any(option.child for part in parts for option in part.options)
    scope = _Scope(partitions=set(), states=set())
    for part_id in recipe.draw_order:
        part = recipe.partition(part_id)
        path = f"partitions.{part.id}"
        if len({option.id for option in part.options}) != len(part.options):
            raise RecipeError(path, "duplicate option id")
        nones = [option for option in part.options if option.none]
        if len(nones) > 1:
            raise RecipeError(path, "at most one none option")
        if any(option.id == NONE_ID and not option.none for option in part.options):
            raise RecipeError(path, f"option id '{NONE_ID}' is reserved for the none option")
        if part.mode == "one" and part.max_draws != 1:
            raise RecipeError(f"{path}.max_draws", "single-draw partitions draw once")
        for region in part.needs:
            if region not in regions:
                raise RecipeError(f"{path}.needs", f"unknown region '{region}'")
        if part.when is not None:
            _check_condition(recipe, part.when, f"{path}.when", scope)
        if part.quota and part.mode != "one":
            raise RecipeError(
                f"{path}.quota",
                "quota partitions must draw once",
            )
        # Same-partition references are allowed (fill mode sees its own earlier draws).
        own_scope = _Scope(partitions=scope.partitions | {part.id},
                           states=scope.states | _part_states(part))
        for option in part.options:
            opath = f"{path}.options.{option.id}"
            if option.none:
                if option.tags.strip() or option.slots or _placeholders(option.label):
                    raise RecipeError(opath, "the none option has no tags or slots")
                if option.id != NONE_ID:
                    raise RecipeError(opath, f"the none option must use id '{NONE_ID}'")
            elif not option.tags.strip():
                raise RecipeError(f"{opath}.tags", "options need tags (use the none option)")
            if "//" in option.tags:
                raise RecipeError(f"{opath}.tags", "tags cannot contain comment markers")
            for region in option.needs:
                if region not in regions:
                    raise RecipeError(f"{opath}.needs", f"unknown region '{region}'")
            if option.when is not None:
                _check_condition(recipe, option.when, f"{opath}.when", own_scope)
            for index, mod in enumerate(option.weight_mods):
                _check_condition(recipe, mod.when, f"{opath}.weight_mods[{index}]", own_scope)
            names = _placeholders(option.tags)
            if len(names) != len(set(names)):
                raise RecipeError(f"{opath}.tags", "each slot may appear once per option")
            for name in [*names, *option.slots]:
                if name not in slots:
                    raise RecipeError(f"{opath}.tags", f"unknown slot '{name}'")
            if set(option.slots) - set(names):
                raise RecipeError(f"{opath}.slots", "slot settings for a slot not in tags")
            for name, use in option.slots.items():
                values = {value.id for value in slots[name].values}
                listed = set(use.exclude) | set(use.only or []) | set(use.weight_mods)
                if listed - values:
                    raise RecipeError(f"{opath}.slots.{name}", "unknown value ids")
                if use.exclude_state and use.exclude_state not in own_scope.states:
                    raise RecipeError(
                        f"{opath}.slots.{name}.exclude_state",
                        f"state '{use.exclude_state}' is not set by an earlier partition",
                    )
            _effect_refs(recipe, option.effects, f"{opath}.effects", part.id, rule=False)
            if option.child and option.effects.set.get(CHILD_STATE[0]) != CHILD_STATE[1]:
                raise RecipeError(opath, "child options must set state age = child")
            if has_child and not option.child:
                words = " ".join([option.tags, *option.effects.content_add,
                                  *option.effects.style_add])
                if CHILD_UNSAFE.search(words) and not (
                    _guards_adult(option.when) or _guards_adult(part.when)
                ):
                    raise RecipeError(
                        opath, "this content needs the condition 'not state age = child' "
                        "because the recipe has child options",
                    )
        scope.partitions.add(part.id)
        scope.states |= _part_states(part)
    rule_scope = _Scope(partitions=set(ids), states=_state_keys(recipe), rule=True)
    for rule in recipe.rules:
        path = f"rules.{rule.id}"
        _check_condition(recipe, rule.when, f"{path}.when", rule_scope)
        _effect_refs(recipe, rule.effects, f"{path}.effects", None, rule=True)
        words = " ".join([*rule.effects.content_add, *rule.effects.style_add])
        if has_child and CHILD_UNSAFE.search(words) and not _guards_adult(rule.when):
            raise RecipeError(path, "this content needs the condition 'not state age = child'")

def _part_states(part: Partition) -> set[str]:
    keys: set[str] = set()
    for option in part.options:
        keys.update(option.effects.set)
        keys.update(use.set_state for use in option.slots.values() if use.set_state)
    return keys

def ordering_warnings(recipe: DatasetRecipe) -> list[str]:
    """Non-blocking hints: a hide/remove/whitelist target that is drawn before its source."""
    position = {part_id: index for index, part_id in enumerate(recipe.draw_order)}
    descendants = _descendants(recipe)
    warnings: list[str] = []
    for part in recipe.partitions:
        for option in part.options:
            effects = option.effects
            hidden = set().union(*(descendants[region] for region in effects.hide)) if (
                effects.hide) else set()
            targets: set[str] = set(effects.remove_partitions) | set(effects.allow_options)
            targets |= {ref.split(".")[0] for ref in effects.remove_options}
            for other in recipe.partitions:
                if other.id == part.id or position[other.id] > position[part.id]:
                    continue
                needs = set(other.needs) | {r for o in other.options for r in o.needs}
                if other.id in targets or needs & hidden:
                    warnings.append(
                        f"{part.id}.{option.id} affects '{other.id}', which is drawn earlier; "
                        "an already drawn result is withdrawn instead of skipped",
                    )
    return warnings

def _descendants(recipe: DatasetRecipe) -> dict[str, set[str]]:
    children: dict[str, list[str]] = {region.id: [] for region in recipe.regions}
    for region in recipe.regions:
        if region.parent:
            children[region.parent].append(region.id)
    result: dict[str, set[str]] = {}
    for region in recipe.regions:
        stack, seen = [region.id], set()
        while stack:
            current = stack.pop()
            if current not in seen:
                seen.add(current)
                stack.extend(children[current])
        result[region.id] = seen
    return result

# --------------------------------------------------------------------------- sampling

@dataclass
class _Draw:
    partition: str
    option: Option
    values: dict[str, str]
    tags: list[str]
    label: str
    withdrawn_by: str | None = None

@dataclass
class _Item:
    recipe: DatasetRecipe
    descendants: dict[str, set[str]]
    draws: list[_Draw] = field(default_factory=list)
    skips: dict[str, str] = field(default_factory=dict)
    removed: list[tuple[_Draw, str]] = field(default_factory=list)
    rule_hits: list[Rule] = field(default_factory=list)
    content_ops: list[tuple[str, str, str]] = field(default_factory=list)
    style_ops: list[tuple[str, str]] = field(default_factory=list)
    stale: bool = False

    @property
    def active(self) -> list[_Draw]:
        return [draw for draw in self.draws if draw.withdrawn_by is None]

    def hidden(self) -> set[str]:
        hidden: set[str] = set()
        for draw in self.active:
            for region in draw.option.effects.hide:
                hidden |= self.descendants[region]
        return hidden

    def visible(self, region: str) -> bool:
        return region not in self.hidden()

    def state(self) -> dict[str, str]:
        state: dict[str, str] = {}
        for draw in self.active:
            state.update(draw.option.effects.set)
            for name, use in draw.option.slots.items():
                if use.set_state and name in draw.values:
                    state[use.set_state] = draw.values[name]
        return state

    def capacity(self) -> dict[str, int]:
        left = dict(self.recipe.resources)
        for draw in self.active:
            for resource, amount in draw.option.effects.consume.items():
                left[resource] -= amount
        return left

    def _effects(self) -> list[Effects]:
        return [draw.option.effects for draw in self.active] + [
            rule.effects for rule in self.rule_hits
        ]

    def removed_partitions(self) -> set[str]:
        return {pid for effects in self._effects() for pid in effects.remove_partitions}

    def removed_options(self) -> set[str]:
        return {ref for effects in self._effects() for ref in effects.remove_options}

    def allowed(self, partition_id: str) -> set[str] | None:
        result: set[str] | None = None
        for effects in self._effects():
            if partition_id in effects.allow_options:
                listed = set(effects.allow_options[partition_id])
                result = listed if result is None else result & listed
        return result

    def allowed_values(self, key: str) -> set[str] | None:
        result: set[str] | None = None
        for effects in self._effects():
            if key in effects.allow_values:
                listed = set(effects.allow_values[key])
                result = listed if result is None else result & listed
        return result

    def chosen(self, partition_id: str) -> list[_Draw]:
        return [draw for draw in self.active if draw.partition == partition_id]

    def content_keys(self) -> set[str]:
        keys = {tag_key(tag) for draw in self.active for tag in draw.tags}
        for op, tag, _group in self.content_ops:
            if op == "add":
                keys.add(tag_key(tag))
            else:
                keys.discard(tag_key(tag))
        return keys

    def evaluate(self, condition: Condition | None) -> bool:
        if condition is None:
            return True
        if "all" in condition:
            return all(self.evaluate(child) for child in condition["all"])
        if "any" in condition:
            return any(self.evaluate(child) for child in condition["any"])
        if "not" in condition:
            return not self.evaluate(condition["not"])
        if "chosen" in condition:
            partition_id, option_id = condition["chosen"].split(".")
            return any(draw.option.id == option_id for draw in self.chosen(partition_id))
        if "partition_drawn" in condition:
            return any(not draw.option.none for draw in self.chosen(condition["partition_drawn"]))
        if "state" in condition:
            return self.state().get(condition["state"]) in condition["in"]
        if "visible" in condition:
            return self.visible(condition["visible"])
        if "tag" in condition:
            return tag_key(condition["tag"]) in self.content_keys()
        return False

    def withdraw(self, source: str, label: str) -> None:
        """Withdraw draws that a newly applied effect removes or no longer allows."""
        removed_parts, removed_options = self.removed_partitions(), self.removed_options()
        changed = True
        while changed:
            changed = False
            for index, draw in enumerate(self.draws):
                if draw.withdrawn_by is not None:
                    continue
                ref = f"{draw.partition}.{draw.option.id}"
                allowed = self.allowed(draw.partition)
                bad_value = any(
                    (values := self.allowed_values(f"{ref}.{name}")) is not None
                    and value not in values
                    for name, value in draw.values.items()
                )
                if (
                    draw.partition in removed_parts or ref in removed_options
                    or (allowed is not None and draw.option.id not in allowed) or bad_value
                ):
                    draw.withdrawn_by = source
                    self.removed.append((draw, label))
                    later = self.draws[index + 1:]
                    if draw.option.effects.structural() and any(
                        other.withdrawn_by is None and other.partition != draw.partition
                        for other in later
                    ):
                        self.stale = True
                    changed = True
                    removed_parts, removed_options = (
                        self.removed_partitions(), self.removed_options(),
                    )

def _weighted(rng: random.Random, choices: list[tuple[Any, float]]) -> Any:
    total = sum(weight for _, weight in choices)
    point = rng.random() * total
    for value, weight in choices:
        point -= weight
        if point < 0:
            return value
    return choices[-1][0]

def _quota(
    rng: random.Random, choices: list[tuple[Option, float]], n: int,
) -> list[str]:
    total = sum(weight for _, weight in choices)
    exact = [(option, weight * n / total) for option, weight in choices]
    counts = {option.id: int(share) for option, share in exact}
    rest = n - sum(counts.values())
    # Random tie breaking avoids consistently favoring the first option in small batches.
    order = list(exact)
    rng.shuffle(order)
    order.sort(key=lambda pair: -(pair[1] - int(pair[1])))
    for option, _ in order[:rest]:
        counts[option.id] += 1
    plan = [option.id for option, _ in choices for _ in range(counts[option.id])]
    rng.shuffle(plan)
    return plan

class Sampler:
    def __init__(self, recipe: DatasetRecipe):
        self.recipe = recipe
        self.slots = {slot.id: slot for slot in recipe.slots}
        self.parts = {part.id: part for part in recipe.partitions}
        self.descendants = _descendants(recipe)
        self.slot_counts: dict[tuple, dict[str, int]] = {}

    def _slot_value(self, rng: random.Random, name: str, choices: list[tuple[str, float]]) -> str:
        """Balance repeated draws of the same legal slot values, including exclusions."""
        counts = self.slot_counts.setdefault((name, tuple(choices)), {})
        total = sum(weight for _, weight in choices)
        ordinal = sum(counts.values()) + 1
        ranked = [(value, ordinal * weight / total - counts.get(value, 0))
                  for value, weight in choices]
        best = max(score for _, score in ranked)
        tied = [value for value, score in ranked if abs(score - best) < 1e-9]
        value = rng.choice(tied)
        counts[value] = counts.get(value, 0) + 1
        return value

    def _value_choices(
        self, item: _Item, partition_id: str, option: Option, name: str,
    ) -> list[tuple[str, float]]:
        use = option.slots.get(name, SlotUse())
        allowed = item.allowed_values(f"{partition_id}.{option.id}.{name}")
        state = item.state()
        avoid = state.get(use.exclude_state) if use.exclude_state else None
        choices = []
        for value in self.slots[name].values:
            if value.id in use.exclude or (use.only is not None and value.id not in use.only):
                continue
            if (allowed is not None and value.id not in allowed) or value.id == avoid:
                continue
            weight = value.weight * use.weight_mods.get(value.id, 1)
            if weight > 0:
                choices.append((value.id, weight))
        return choices

    def _choices(self, item: _Item, part: Partition) -> list[tuple[Option, float]]:
        """Eligible options with weights; the item is not mutated while filtering,
        so its derived state is computed once per call instead of once per option."""
        chosen = {draw.option.id for draw in item.chosen(part.id)}
        removed = item.removed_options()
        allowed = item.allowed(part.id)
        hidden = item.hidden()
        capacity = item.capacity()
        choices: list[tuple[Option, float]] = []
        for option in part.options:
            if option.disabled or option.id in chosen:
                continue
            if f"{part.id}.{option.id}" in removed:
                continue
            if allowed is not None and option.id not in allowed:
                continue
            if any(region in hidden for region in option.needs):
                continue
            if not item.evaluate(option.when):
                continue
            if any(capacity[res] < amount for res, amount in option.effects.consume.items()):
                continue
            if any(not self._value_choices(item, part.id, option, name)
                   for name in _placeholders(option.tags)):
                continue
            weight = option.weight * self._mods(item, option)
            if weight > 0:
                choices.append((option, weight))
        return choices

    @staticmethod
    def _mods(item: _Item, option: Option) -> float:
        factor = 1.0
        for mod in option.weight_mods:
            if item.evaluate(mod.when):
                factor *= mod.factor
        return factor

    def _fill(self, rng: random.Random, item: _Item, part: Partition, option: Option) -> _Draw:
        values: dict[str, str] = {}
        text, label = option.tags, option.label
        for name in _placeholders(option.tags):
            # Drawn one by one so a later slot's exclude_state can see the earlier value.
            value_id = self._slot_value(
                rng, name, self._value_choices(item, part.id, option, name),
            )
            value = next(v for v in self.slots[name].values if v.id == value_id)
            values[name] = value_id
            text = text.replace("{" + name + "}", value.tag)
            label = label.replace("{" + name + "}", value.label or value.tag)
        label = label or text or "无"
        return _Draw(part.id, option, values, split_tags(text),
                     f"{part.label or part.id}：{label}")

    def _skip_reason(self, item: _Item, part: Partition) -> str | None:
        if part.id in item.removed_partitions():
            return "removed"
        hidden = item.hidden()
        if any(region in hidden for region in part.needs):
            return "invisible"
        if not item.evaluate(part.when):
            return "condition"
        return None

    def draw_partition(
        self, rng: random.Random, item: _Item, part: Partition, planned: str | None = None,
    ) -> None:
        reason = self._skip_reason(item, part)
        if reason:
            item.skips[part.id] = reason
            return
        count = 0
        while count < part.max_draws:
            choices = self._choices(item, part)
            # Only "none" left means every real option conflicts: that is a skip, not
            # a deliberate none, so the none option's effects must not apply.
            if not choices or all(option.none for option, _ in choices):
                if count == 0:
                    item.skips[part.id] = "conflict"
                break
            option = None
            if planned is not None:
                option = next((choice for choice, _ in choices if choice.id == planned), None)
            if option is None:
                option = _weighted(rng, choices)
            if option.none and count > 0:
                break  # fill mode: none stops further draws without applying effects
            draw = self._fill(rng, item, part, option)
            item.draws.append(draw)
            for tag in option.effects.content_add:
                item.content_ops.append(("add", tag, part.id))
            for tag in option.effects.remove_tags:
                item.content_ops.append(("remove", tag, part.id))
            for tag in option.effects.style_add:
                item.style_ops.append(("add", tag))
            for tag in option.effects.style_remove:
                item.style_ops.append(("remove", tag))
            if option.effects.structural():
                item.withdraw(f"{part.id}.{option.id}", draw.label)
            count += 1
            if option.none or part.mode == "one":
                break

    def apply_rules(self, item: _Item) -> None:
        for rule in self.recipe.rules:
            if rule.disabled or not item.evaluate(rule.when):
                continue
            item.rule_hits.append(rule)
            item.withdraw(f"rule:{rule.id}", f"规则：{rule.label or rule.id}")
            for tag in rule.effects.content_add:
                item.content_ops.append(("add", tag, "-rule"))
            for tag in rule.effects.remove_tags:
                item.content_ops.append(("remove", tag, "-rule"))
            for tag in rule.effects.style_add:
                item.style_ops.append(("add", tag))
            for tag in rule.effects.style_remove:
                item.style_ops.append(("remove", tag))

    def assemble(self, item: _Item) -> tuple[str, dict[str, list[str]], list[str]]:
        groups: dict[str, list[str]] = {part_id: [] for part_id in self.recipe.output_order}
        groups["-rule"] = []
        for draw in item.active:
            groups[draw.partition].extend(draw.tags)
        for op, tag, group in item.content_ops:
            if op == "add":
                groups[group].append(tag)
            else:
                key = tag_key(tag)
                for tags in groups.values():
                    tags[:] = [t for t in tags if tag_key(t) != key]
        seen: set[str] = set()
        ordered: list[str] = []
        hidden = item.hidden()
        forbidden = {tag_key(binding.tag) for binding in self.recipe.style_tags
                     if binding.needs in hidden}
        for tags in groups.values():
            for fragment in tags:
                for tag in split_tags(fragment):
                    key = tag_key(tag)
                    if key and key not in seen and key not in forbidden:
                        seen.add(key)
                        ordered.append(tag)
        # Invisible-region requirements are final, including after explicit additions.
        edits: dict[str, tuple[str, str]] = {}
        for op, tag in item.style_ops:
            edits[style_tag_key(tag)] = (op, tag)
        region_removed: list[str] = []
        for style_tag in self.recipe.style_tags:
            if style_tag.needs in hidden:
                edits[style_tag_key(style_tag.tag)] = ("remove", style_tag.tag)
                region_removed.append(style_tag.tag)
        style = StyleEdits.model_validate({
            "add": [tag for op, tag in edits.values() if op == "add"],
            "remove": [tag for op, tag in edits.values() if op == "remove"],
        }).model_dump()
        return normalize_prompt(", ".join(ordered)), style, region_removed

def _record(item: _Item, recipe: DatasetRecipe, region_removed: list[str]) -> list[dict]:
    labels = {part.id: part.label or part.id for part in recipe.partitions}
    records: list[dict] = []
    for draw in item.active:
        record = {"partition": draw.partition, "option": draw.option.id, "label": draw.label}
        if draw.values:
            record["values"] = dict(draw.values)
        records.append(record)
    reasons = {"invisible": "不可见", "condition": "条件不满足", "conflict": "冲突",
               "removed": "被移除"}
    for part_id, reason in item.skips.items():
        records.append({"partition": part_id, "option": "-skip", "reason": reason,
                        "label": f"{labels[part_id]}：跳过（{reasons[reason]}）"})
    for draw, by in item.removed:
        records.append({"partition": draw.partition, "option": "-removed",
                        "reason": f"by:{draw.withdrawn_by}",
                        "label": f"{draw.label}（被 {by} 移除）"})
    for rule in item.rule_hits:
        records.append({"partition": "-rule", "option": rule.id,
                        "label": f"规则：{rule.label or rule.id}"})
    for tag in region_removed:
        records.append({"partition": "-style", "option": "region-removed",
                        "label": f"画风：去掉 {tag}"})
    if any(draw.option.child for draw in item.active):
        records.append({"partition": "-meta", "option": "child", "label": "儿童"})
    for record in records:
        record["label"] = record["label"][:100]
    return records[:128]

class SampleItem(BaseModel):
    id: str
    prompt: str
    shape: Literal["portrait", "square", "landscape"] | None = None
    draws: list[dict[str, Any]]
    style_edits: dict[str, list[str]]

class OptionStat(BaseModel):
    option: str
    label: str
    target: float
    count: int

class PartitionStat(BaseModel):
    partition: str
    label: str
    options: list[OptionStat]
    skips: dict[str, int]
    values: dict[str, dict[str, int]]
    quota_misses: int = 0

class SampleStats(BaseModel):
    requested: int
    produced: int
    overflow: int
    stale_dependency: int
    partitions: list[PartitionStat]
    rules: dict[str, int]
    style_removed: dict[str, int]
    style_added: dict[str, int]
    warnings: list[str]

class SampleResult(BaseModel):
    items: list[SampleItem]
    stats: SampleStats

class SampleStyleError(ValueError):
    """The aggregate style edits cannot become a queued dataset item."""

def sample(recipe: DatasetRecipe, n: int, seed: int) -> SampleResult:
    """Draw ``n`` items. The same recipe, n and seed always give the same result."""
    if not 1 <= n <= MAX_ITEMS:
        raise ValueError(f"n must be between 1 and {MAX_ITEMS}")
    rng = random.Random(seed)
    sampler = Sampler(recipe)
    sampled = [_Item(recipe, sampler.descendants) for _ in range(n)]
    quota: dict[str, dict[int, str]] = {}
    targets: dict[str, dict[str, float]] = {}
    for part_id in recipe.draw_order:
        part = sampler.parts[part_id]
        planned: dict[int, str] = {}
        if part.quota:
            # Only items with the same legal choices share a quota. Invisible items
            # never consume a footwear/bangs allocation, and restrictions stay binding.
            buckets: dict[tuple, list[int]] = {}
            for index, item in enumerate(sampled):
                if sampler._skip_reason(item, part):
                    continue
                choices = sampler._choices(item, part)
                if not choices or all(option.none for option, _ in choices):
                    continue
                signature = tuple((option.id, weight) for option, weight in choices)
                buckets.setdefault(signature, []).append(index)
            target = targets.setdefault(part_id, {})
            for signature, indices in buckets.items():
                choices = [(next(o for o in part.options if o.id == oid), weight)
                           for oid, weight in signature]
                plan = _quota(rng, choices, len(indices))
                planned.update(zip(indices, plan, strict=True))
                total = sum(weight for _, weight in choices)
                for option, weight in choices:
                    target[option.id] = target.get(option.id, 0) + len(indices) * weight / total
            quota[part_id] = planned
        for index, item in enumerate(sampled):
            sampler.draw_partition(rng, item, part, planned.get(index))
    for item in sampled:
        sampler.apply_rules(item)
    counts: dict[str, dict[str, int]] = {part.id: {} for part in recipe.partitions}
    skips: dict[str, dict[str, int]] = {part.id: {} for part in recipe.partitions}
    values: dict[str, dict[str, dict[str, int]]] = {part.id: {} for part in recipe.partitions}
    misses: dict[str, int] = {}
    rules: dict[str, int] = {}
    style_removed: dict[str, int] = {}
    style_added: dict[str, int] = {}
    items: list[SampleItem] = []
    overflow = stale = 0
    for index, item in enumerate(sampled):
        try:
            prompt, style, region_removed = sampler.assemble(item)
        except ValidationError as exception:
            first = exception.errors()[0]
            where = ".".join(str(part) for part in first["loc"])
            raise SampleStyleError(
                f"items.{index}.style_edits.{where}: {first['msg']}",
            ) from exception
        for draw in item.active:
            counts[draw.partition][draw.option.id] = counts[draw.partition].get(
                draw.option.id, 0) + 1
            for name, value in draw.values.items():
                bucket = values[draw.partition].setdefault(name, {})
                bucket[value] = bucket.get(value, 0) + 1
        for part_id, reason in item.skips.items():
            skips[part_id][reason] = skips[part_id].get(reason, 0) + 1
        for part in recipe.partitions:
            if part.quota and index in quota[part.id] and not any(
                draw.option.id == quota[part.id][index] for draw in item.chosen(part.id)
            ):
                misses[part.id] = misses.get(part.id, 0) + 1
        for rule in item.rule_hits:
            rules[rule.id] = rules.get(rule.id, 0) + 1
        for tag in style["remove"]:
            style_removed[tag] = style_removed.get(tag, 0) + 1
        for tag in style["add"]:
            style_added[tag] = style_added.get(tag, 0) + 1
        stale += item.stale
        if not prompt or len(prompt) > MAX_PROMPT:
            overflow += 1
            continue
        shape = None
        for draw in item.active:
            shape = draw.option.size or shape
        items.append(SampleItem(
            id=f"r{seed}-{index + 1:04d}", prompt=prompt, shape=shape,
            draws=_record(item, recipe, region_removed), style_edits=style,
        ))
    partitions = []
    for part in recipe.partitions:
        enabled = [option for option in part.options if not option.disabled]
        total = sum(option.weight for option in enabled)
        partitions.append(PartitionStat(
            partition=part.id, label=part.label,
            options=[
                OptionStat(option=option.id, label=option.label or option.tags or "无",
                           target=(targets[part.id].get(option.id, 0) / len(quota[part.id])
                                   if part.quota and quota[part.id]
                                   else 0 if option.disabled or not total
                                   else option.weight / total),
                           count=counts[part.id].get(option.id, 0))
                for option in part.options
            ],
            skips=skips[part.id], values=values[part.id], quota_misses=misses.get(part.id, 0),
        ))
    return SampleResult(items=items, stats=SampleStats(
        requested=n, produced=len(items), overflow=overflow, stale_dependency=stale,
        partitions=partitions, rules=rules, style_removed=style_removed,
        style_added=style_added, warnings=ordering_warnings(recipe),
    ))

# --------------------------------------------------------------------------- style edits

_OPEN = re.compile(r"^((?:\s*(?:[{\[]|[+-]?(?:\d+(?:\.\d+)?|\.\d+)::))*)")
_CLOSE = re.compile(r"((?:(?:[}\]]|::)\s*)*)$")

def _piece_key(piece: str) -> tuple[str, str, str]:
    opener = _OPEN.match(piece).group(1)
    rest = piece[len(opener):]
    closer = _CLOSE.search(rest).group(1)
    body = rest[: len(rest) - len(closer)] if closer else rest
    return opener, style_tag_key(body), closer

def resolve_style(style: str, edits: dict[str, list[str]] | None) -> str:
    """Apply per-item style edits: remove tags (weight syntax aware), then append tags.

    Hidden ``//`` comment lines are left untouched. Removing a tag keeps any weight or
    emphasis markers attached to it so surrounding groups stay balanced.
    """
    if not edits or not (edits.get("add") or edits.get("remove")):
        return style
    normalized = StyleEdits.model_validate(edits)
    remove = {style_tag_key(tag) for tag in normalized.remove}
    present: set[str] = set()
    lines = style.split("\n")
    for line_index, line in enumerate(lines):
        if line.lstrip().startswith("//"):
            continue
        pieces = split_style_pieces(line)
        kept: list[str] = []
        for piece in pieces:
            opener, key, closer = _piece_key(piece)
            if key and key in remove:
                if opener.strip() or closer.strip():
                    lead = " " if kept else ""
                    kept.append(f"{lead}{opener.strip()}{closer.strip()}")
                continue
            if key:
                present.add(key)
            kept.append(piece)
        lines[line_index] = ",".join(kept)
    result = "\n".join(lines)
    # Tidy separators left by removed tags without touching text inside tags.
    result = re.sub(r"(,\s*)+,", ",", result)
    result = re.sub(r"^\s*,\s*", "", result, flags=re.MULTILINE)
    result = re.sub(r"\s*,\s*$", "", result, flags=re.MULTILINE)
    additions = []
    for tag in normalized.add:
        key = style_tag_key(tag)
        if key and key not in present and key not in {style_tag_key(a) for a in additions}:
            additions.append(tag.strip())
    if additions:
        visible = "\n".join(
            line for line in result.split("\n") if not line.lstrip().startswith("//")
        )
        base = result.rstrip()
        suffix = unclosed_style_suffix(visible)
        if suffix:
            joiner = "\n" if base.split("\n")[-1].lstrip().startswith("//") else " "
            base += f"{joiner}{suffix}"
        joiner = ", " if visible.strip() else ""
        if base.split("\n")[-1].lstrip().startswith("//"):
            joiner = "\n"
        result = f"{base}{joiner}{', '.join(additions)}"
    return result
