"""Private editor metadata with an exact projection onto effective prompts."""

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .prompt_comments import compile_prompt_comments

SharedSectionKey = Literal["scene", "other"]
CharacterSectionKey = Literal[
    "character",
    "upper_clothing",
    "lower_clothing",
    "action",
    "tags",
    "special",
    "other",
]


class PromptSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=3000)
    enabled: bool = Field(default=True, strict=True)


def compose_sections(sections: Iterable[PromptSection], *, prompt_comments: bool = False) -> str:
    parts = [
        text for section in sections if section.enabled
        if (text := (
            compile_prompt_comments(section.text) if prompt_comments else section.text
        )).strip()
    ]
    if len(parts) == 1:
        return parts[0]
    return ", ".join(part.strip() for part in parts)


class SharedSections(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: PromptSection
    other: PromptSection

    def compose(self, *, prompt_comments: bool = False) -> str:
        return compose_sections((self.scene, self.other), prompt_comments=prompt_comments)


class CharacterSections(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character: PromptSection
    upper_clothing: PromptSection
    lower_clothing: PromptSection
    action: PromptSection
    tags: PromptSection
    special: PromptSection
    other: PromptSection

    def compose(self, *, prompt_comments: bool = False) -> str:
        return compose_sections(
            (
                self.character,
                self.upper_clothing,
                self.lower_clothing,
                self.action,
                self.tags,
                self.special,
                self.other,
            ), prompt_comments=prompt_comments,
        )


class SectionCharacter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: CharacterSections
    # Omit the enabled default so legacy frozen run definitions remain byte-compatible.
    enabled: bool = Field(default=True, strict=True, exclude_if=lambda value: value)
    x: float = Field(default=0.5, ge=0.1, le=0.9, allow_inf_nan=False, strict=True)
    y: float = Field(default=0.5, ge=0.1, le=0.9, allow_inf_nan=False, strict=True)


class PromptSections(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    shared: SharedSections
    characters: list[SectionCharacter] = Field(max_length=6)

    @field_validator("version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Section metadata version must be an integer")
        return value

    def effective_characters(
        self, *, prompt_comments: bool = False,
    ) -> list[dict[str, str | float]]:
        return [
            {"prompt": prompt, "x": character.x, "y": character.y}
            for character in self.characters
            if character.enabled
            if (prompt := character.sections.compose(prompt_comments=prompt_comments)).strip()
        ]
