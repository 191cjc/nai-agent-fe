"""Fixed-style dataset runs: one frozen content prompt and derived seed per ordinal."""

import json
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .generations import DatasetItem, ExperimentContext, GenerationRequest
from .prompt_comments import prompt_lines

MAX_SEED = 4294967295


def item_seed(base: int, ordinal: int) -> int:
    """Vary seeds per item for training diversity while staying reproducible."""
    return (base - 1 + ordinal - 1) % MAX_SEED + 1


def dataset_parameters(
    parameters: GenerationRequest, item: DatasetItem, *, seed: int | None,
    context: ExperimentContext | None = None,
) -> GenerationRequest:
    return GenerationRequest.model_validate({
        **parameters.model_dump(mode="json"), "positive_prompt": item.prompt, "seed": seed,
        "experiment": context,
    })


class DatasetRunCreate(BaseModel):
    id: UUID
    parameters: GenerationRequest
    items: list[DatasetItem] = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def valid_plan(self) -> Self:
        parameters = self.parameters
        if parameters.experiment is not None:
            raise ValueError("Run parameters must not inherit experiment identity")
        if (
            parameters.positive_prompt or parameters.character_prompts
            or parameters.prompt_sections is not None
        ):
            raise ValueError("Dataset run content comes only from its items")
        if not parameters.effective_style_prompt.strip():
            raise ValueError("Dataset runs require a style prompt")
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Duplicate dataset item id")
        for item in self.items:
            # A comment line would silently drop content the caption still claims.
            if parameters.prompt_comments and any(
                hidden for _start, _end, hidden in prompt_lines(item.prompt)
            ):
                raise ValueError("Dataset prompts cannot contain comment lines")
            dataset_parameters(parameters, item, seed=parameters.seed)
        return self

    def definition(self) -> tuple[str, str]:
        definition = {
            "kind": "dataset",
            "parameters": self.parameters.model_dump(mode="json"),
            "items": [item.model_dump() for item in self.items],
        }
        return json.dumps(definition, sort_keys=True, separators=(",", ":")), str(len(self.items))
