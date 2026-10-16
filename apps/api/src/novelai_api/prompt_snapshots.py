"""Immutable account-private prompt text snapshots, independent of generation."""

import json
import sqlite3
import time
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .db import Database
from .prompt_sections import CharacterSectionKey, SharedSectionKey


class SharedSnapshotEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["shared"]
    section: SharedSectionKey
    text: str = Field(max_length=3000)


class CharacterSnapshotEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["character"]
    character_index: int = Field(ge=0, le=5, strict=True)
    section: CharacterSectionKey
    text: str = Field(max_length=3000)


PromptSnapshotEntry = Annotated[
    SharedSnapshotEntry | CharacterSnapshotEntry,
    Field(discriminator="scope"),
]


class PromptSnapshotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str = Field(min_length=1, max_length=100)
    entries: list[PromptSnapshotEntry] = Field(min_length=1, max_length=44)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Snapshot name cannot be blank")
        return value

    @model_validator(mode="after")
    def valid_entries(self) -> Self:
        keys = [
            (entry.scope, getattr(entry, "character_index", None), entry.section)
            for entry in self.entries
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate snapshot section")
        if not any(entry.text.strip() for entry in self.entries):
            raise ValueError("Snapshot must contain text")
        return self


class PromptSnapshot(PromptSnapshotCreate):
    created_at: int


class PromptSnapshotSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    created_at: int
    entry_count: int


class PromptSnapshotPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PromptSnapshotSummary]
    next_offset: int | None


class PromptSnapshotConflict(Exception):
    """An existing snapshot ID has different immutable content."""


class PromptSnapshotStore:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _snapshot(row: sqlite3.Row) -> PromptSnapshot:
        return PromptSnapshot(
            id=row["id"],
            name=row["name"],
            entries=json.loads(row["entries_json"]),
            created_at=row["created_at"],
        )

    def create(self, user_id: str, request: PromptSnapshotCreate) -> PromptSnapshot:
        snapshot_id = str(request.id)
        entries = [entry.model_dump(mode="json") for entry in request.entries]
        with self.database.connect(write=True) as connection:
            existing = connection.execute(
                "SELECT * FROM prompt_snapshots WHERE user_id = ? AND id = ?",
                (user_id, snapshot_id),
            ).fetchone()
            if existing:
                if (
                    existing["name"] != request.name
                    or json.loads(existing["entries_json"]) != entries
                ):
                    raise PromptSnapshotConflict("Snapshot content changed")
                return self._snapshot(existing)
            connection.execute(
                "INSERT INTO prompt_snapshots (user_id, id, name, entries_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    user_id,
                    snapshot_id,
                    request.name,
                    json.dumps(entries, ensure_ascii=False, separators=(",", ":")),
                    int(time.time()),
                ),
            )
            row = connection.execute(
                "SELECT * FROM prompt_snapshots WHERE user_id = ? AND id = ?",
                (user_id, snapshot_id),
            ).fetchone()
        return self._snapshot(row)

    def get(self, user_id: str, snapshot_id: str) -> PromptSnapshot | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM prompt_snapshots WHERE user_id = ? AND id = ?",
                (user_id, snapshot_id),
            ).fetchone()
        return self._snapshot(row) if row else None

    def list(self, user_id: str, *, limit: int, offset: int) -> PromptSnapshotPage:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, created_at, json_array_length(entries_json) AS entry_count "
                "FROM prompt_snapshots WHERE user_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (user_id, limit + 1, offset),
            ).fetchall()
        return PromptSnapshotPage(
            items=[PromptSnapshotSummary(**dict(row)) for row in rows[:limit]],
            next_offset=offset + limit if len(rows) > limit else None,
        )

    def delete(self, user_id: str, snapshot_id: str) -> bool:
        with self.database.connect(write=True) as connection:
            result = connection.execute(
                "DELETE FROM prompt_snapshots WHERE user_id = ? AND id = ?",
                (user_id, snapshot_id),
            )
        return result.rowcount == 1
