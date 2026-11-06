"""Paid re-runs of finished training-set groups: one source group, a new random seed.

Shared by the single re-run endpoint and durable re-run batches (style_experiments).
"""

from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, ValidationError, model_validator

from .dataset_plan import has_comment_line
from .generations import GenerationRequest, HistoryItem
from .prompt_comments import compile_prompt_comments

# One review-grid batch never exceeds the grid's loaded group cap.
MAX_RERUN_BATCH = 3000


class RerunEdits(BaseModel):
    # Image of the source job to mark discarded once the re-run is accepted.
    discard_index: int | None = Field(default=None, ge=0, le=7)
    # Optional owner edits for this one re-run: the item's content prompt (it also becomes
    # the re-run's caption) and the style. Absent keeps the source group's frozen values.
    prompt: str | None = Field(default=None, min_length=1, max_length=1000)
    style_prompt: str | None = Field(default=None, min_length=1, max_length=3000)


class RerunBatchItem(RerunEdits):
    job_id: Annotated[str, StringConstraints(min_length=1, max_length=64)]


class RerunBatchCreate(BaseModel):
    id: UUID
    # The training set (dataset run) every source group belongs to.
    experiment_id: UUID
    items: list[RerunBatchItem] = Field(min_length=1, max_length=MAX_RERUN_BATCH)
    name: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def strip_name(self) -> Self:
        if self.name is not None:
            self.name = self.name.strip() or None
        return self


class RerunRefused(Exception):
    def __init__(
        self,
        code: Literal["rerun_unsupported", "job_active", "rerun_image_missing", "rerun_invalid"],
        message: str,
    ):
        self.code = code
        self.message = message
        super().__init__(code)


def rerun_parameters(job: HistoryItem, edits: RerunEdits) -> GenerationRequest:
    """The frozen source group with a new random seed, one sample and the owner's edits."""
    context = job.parameters.experiment
    if context is None or context.kind != "dataset":
        raise RerunRefused("rerun_unsupported", "Only training-set images can be re-run")
    if job.status not in ("succeeded", "failed"):
        raise RerunRefused("job_active", "Generation is still running")
    if edits.discard_index is not None and (
        job.status != "succeeded" or not 0 <= edits.discard_index < job.image_count
    ):
        raise RerunRefused("rerun_image_missing", "Image not found")
    source = job.parameters
    update: dict = {"seed": None, "sample_count": 1}
    item = context.item
    if edits.prompt is not None and item is not None and edits.prompt != item.prompt:
        if source.prompt_comments and has_comment_line(edits.prompt):
            raise RerunRefused("rerun_invalid", "Training prompts cannot contain comment lines")
        old_item = item.prompt.strip()
        if source.reference is None:
            positive = edits.prompt
        elif source.positive_prompt.endswith(old_item):
            # Character groups send "<traits>, <item prompt>"; keep the traits.
            positive = source.positive_prompt[: len(source.positive_prompt) - len(old_item)] \
                + edits.prompt.strip()
        else:
            raise RerunRefused("rerun_invalid", "This group's prompt cannot be edited")
        update["positive_prompt"] = positive
        item = item.model_copy(update={"prompt": edits.prompt})
    if edits.style_prompt is not None and edits.style_prompt != source.style_prompt:
        effective = (
            compile_prompt_comments(edits.style_prompt) if source.prompt_comments
            else edits.style_prompt
        )
        if not effective.strip():
            raise RerunRefused("rerun_invalid", "Style prompt cannot be blank")
        update["style_prompt"] = edits.style_prompt
    experiment = context.model_copy(update={"rerun_of": job.id, "item": item})
    if len(update) == 2:
        # No edits: the frozen source as before (never re-validated against newer rules).
        return source.model_copy(update={**update, "experiment": experiment})
    try:
        return GenerationRequest.model_validate({
            **source.model_dump(mode="json"), **update,
            "experiment": experiment.model_dump(mode="json"),
        })
    except ValidationError:
        raise RerunRefused(
            "rerun_invalid", "Edited prompt or style is not a valid request",
        ) from None
