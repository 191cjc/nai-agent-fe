"""Dataset runs: one frozen prompt, derived seed and optional style/reference per ordinal."""

import json
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from .generations import (
    DatasetItem,
    ExperimentContext,
    GenerationRequest,
    ReferenceImageUse,
    ReferenceUse,
)
from .prompt_comments import compile_prompt_comments, prompt_lines

MAX_SEED = 4294967295
# Validation-only stand-in so model/mode rules run before owner references are resolved.
_PLACEHOLDER_IMAGE = ReferenceImageUse(id="00000000-0000-0000-0000-000000000000", sha256="0" * 64)


def item_seed(base: int, ordinal: int) -> int:
    """Vary seeds per item for training diversity while staying reproducible."""
    return (base - 1 + ordinal - 1) % MAX_SEED + 1


def _has_comment_line(text: str) -> bool:
    return any(hidden for _start, _end, hidden in prompt_lines(text))


class CharacterRequest(BaseModel):
    traits: str = Field(min_length=1, max_length=1000)
    mode: Literal["vibe", "img2img", "gpt"]
    reference_ids: list[UUID] = Field(min_length=1, max_length=4)
    strength: float | None = Field(default=None, ge=0.01, le=0.99, allow_inf_nan=False)
    noise: float | None = Field(default=None, ge=0, le=0.99, allow_inf_nan=False)
    # Vibe only: encode_vibe identity strength (upstream default 1.0 when absent).
    information_extracted: float | None = Field(
        default=None, ge=0.01, le=1.0, allow_inf_nan=False,
    )
    # Vibe only: generation-time vibe influence (upstream default 1.0 when absent).
    reference_strength: float | None = Field(
        default=None, ge=0.01, le=1.0, allow_inf_nan=False,
    )
    gpt_quality: Literal["low", "medium", "high"] | None = None

    @field_validator("traits")
    @classmethod
    def nonblank_traits(cls, value: str) -> str:
        if not value.strip() or _has_comment_line(value):
            raise ValueError("Character traits must be visible, non-blank tags")
        return value

    @model_validator(mode="after")
    def valid_mode(self) -> Self:
        if len(set(self.reference_ids)) != len(self.reference_ids):
            raise ValueError("Duplicate reference image")
        if self.mode == "img2img" and (self.strength is None or self.noise is None):
            raise ValueError("Image-to-image requires strength and noise")
        if self.mode in ("vibe", "gpt") and (self.strength is not None or self.noise is not None):
            raise ValueError("Only image-to-image has strength and noise")
        if self.mode == "gpt" and (
            self.information_extracted is not None or self.reference_strength is not None
        ):
            raise ValueError("GPT image mode has no vibe settings")
        if self.mode != "gpt" and self.gpt_quality is not None:
            raise ValueError("Only GPT image mode has gpt_quality")
        if self.mode == "img2img" and (
            self.information_extracted is not None or self.reference_strength is not None
        ):
            raise ValueError("Image-to-image has no information_extracted or reference_strength")
        return self


class CharacterPlan(BaseModel):
    """Frozen character block: reference ids are pinned to their digests at creation."""

    traits: str
    mode: Literal["vibe", "img2img", "gpt"]
    references: list[ReferenceImageUse] = Field(min_length=1, max_length=4)
    strength: float | None = None
    noise: float | None = None
    information_extracted: float | None = None
    reference_strength: float | None = None
    gpt_quality: Literal["low", "medium", "high"] | None = None

    def use(self, ordinal: int) -> ReferenceUse:
        if self.mode == "gpt":
            # Every GPT item sees all references, like vibe transfer.
            return ReferenceUse(mode="gpt", images=self.references, gpt_quality=self.gpt_quality)
        if self.mode == "vibe":
            return ReferenceUse(
                mode="vibe", images=self.references,
                information_extracted=self.information_extracted,
                reference_strength=self.reference_strength,
            )
        image = self.references[(ordinal - 1) % len(self.references)]
        return ReferenceUse(
            mode="img2img", images=[image], strength=self.strength, noise=self.noise,
        )


def dataset_parameters(
    parameters: GenerationRequest, item: DatasetItem, *, seed: int | None,
    context: ExperimentContext | None = None, ordinal: int = 1,
    styles: list[str] | None = None, character: CharacterPlan | None = None,
) -> GenerationRequest:
    update: dict = {"positive_prompt": item.prompt, "seed": seed, "experiment": context}
    if item.characters:
        # Explicit per-person positions; the request validator rejects non-native models
        # and reference (character-run) groups for items that carry characters.
        update["character_prompts"] = [character.model_dump() for character in item.characters]
        update["auto_character_position"] = False
    if styles:
        update["style_prompt"] = styles[(ordinal - 1) % len(styles)]
    if character is not None:
        update["positive_prompt"] = f"{character.traits.strip()}, {item.prompt.strip()}"
        update["reference"] = character.use(ordinal)
    return GenerationRequest.model_validate({**parameters.model_dump(mode="json"), **update})


class DatasetRunCreate(BaseModel):
    id: UUID
    parameters: GenerationRequest
    items: list[DatasetItem] = Field(min_length=1, max_length=300)
    # Optional rotation pool; absent keeps the single frozen style (stored runs unchanged).
    styles: list[str] | None = Field(default=None, min_length=1, max_length=8)
    character: CharacterRequest | None = None

    @model_validator(mode="after")
    def valid_plan(self) -> Self:
        parameters = self.parameters
        if parameters.experiment is not None or parameters.reference is not None:
            raise ValueError("Run parameters must not inherit experiment or reference identity")
        if (
            parameters.positive_prompt or parameters.character_prompts
            or parameters.prompt_sections is not None
        ):
            raise ValueError("Dataset run content comes only from its items")
        if not parameters.effective_style_prompt.strip():
            raise ValueError("Dataset runs require a style prompt")
        styles = self.styles or [parameters.style_prompt]
        if self.styles is not None:
            if parameters.style_prompt != self.styles[0]:
                raise ValueError("The first pooled style must equal the frozen style prompt")
            for style in self.styles:
                effective = compile_prompt_comments(style) if parameters.prompt_comments else style
                if len(style) > 3000 or not effective.strip():
                    raise ValueError("Each pooled style must be a non-blank prompt")
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Duplicate dataset item id")
        character = None
        if self.character is not None:
            character = CharacterPlan(
                traits=self.character.traits, mode=self.character.mode,
                references=[_PLACEHOLDER_IMAGE] * len(self.character.reference_ids),
                strength=self.character.strength, noise=self.character.noise,
                information_extracted=self.character.information_extracted,
                reference_strength=self.character.reference_strength,
                gpt_quality=self.character.gpt_quality,
            )
        # The longest effective style bounds every rotated style/item combination.
        longest = max(
            range(len(styles)),
            key=lambda index: len(
                (compile_prompt_comments(styles[index]) if parameters.prompt_comments
                 else styles[index]).strip(),
            ),
        )
        for item in self.items:
            # A comment line would silently drop content the caption still claims.
            if parameters.prompt_comments and any(
                _has_comment_line(text)
                for text in (item.prompt, *(character.prompt for character in item.characters))
            ):
                raise ValueError("Dataset prompts cannot contain comment lines")
            dataset_parameters(
                parameters, item, seed=parameters.seed, ordinal=longest + 1,
                styles=self.styles, character=character,
            )
        return self

    def definition(
        self, references: list[ReferenceImageUse] | None = None,
    ) -> tuple[str, str]:
        definition: dict = {
            "kind": "dataset",
            "parameters": self.parameters.model_dump(mode="json"),
            "items": [item.model_dump() for item in self.items],
        }
        if self.styles is not None:
            definition["styles"] = self.styles
        if self.character is not None:
            if references is None or len(references) != len(self.character.reference_ids):
                raise ValueError("Character references must be resolved for the owner")
            definition["character"] = CharacterPlan(
                traits=self.character.traits, mode=self.character.mode, references=references,
                strength=self.character.strength, noise=self.character.noise,
                information_extracted=self.character.information_extracted,
                reference_strength=self.character.reference_strength,
                gpt_quality=self.character.gpt_quality,
            ).model_dump(mode="json", exclude_none=True)
        return json.dumps(definition, sort_keys=True, separators=(",", ":")), str(len(self.items))
