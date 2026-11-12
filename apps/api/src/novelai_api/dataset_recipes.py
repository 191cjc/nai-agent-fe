"""Owner-private stored random-dataset recipes."""

import json
import sqlite3
import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .db import Database
from .recipe_engine import MAX_ITEMS, DatasetRecipe

MAX_RECIPES = 100

class RecipeSummary(BaseModel):
    id: UUID
    name: str
    updated_at: int

class StoredRecipe(RecipeSummary):
    recipe: DatasetRecipe
    created_at: int

class RecipeSave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    recipe: DatasetRecipe
    # Optimistic concurrency: the updated_at the editor loaded; absent creates/overwrites.
    expected_updated_at: int | None = None

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Recipe name cannot be blank")
        return value.strip()

class SampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipe: DatasetRecipe
    n: int = Field(ge=1, le=MAX_ITEMS)
    seed: int = Field(ge=0, le=4294967295)

class RecipeConflict(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code

class RecipeStore:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _stored(row: sqlite3.Row) -> StoredRecipe:
        return StoredRecipe(
            id=row["id"], name=row["name"], updated_at=row["updated_at"],
            created_at=row["created_at"],
            recipe=DatasetRecipe.model_validate(json.loads(row["recipe_json"])),
        )

    def list(self, user_id: str) -> list[RecipeSummary]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, updated_at FROM dataset_recipes WHERE user_id = ? "
                "ORDER BY updated_at DESC, id", (user_id,),
            ).fetchall()
        return [RecipeSummary(**dict(row)) for row in rows]

    def get(self, user_id: str, recipe_id: str) -> StoredRecipe | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM dataset_recipes WHERE user_id = ? AND id = ?",
                (user_id, recipe_id),
            ).fetchone()
        return self._stored(row) if row else None

    def save(self, user_id: str, recipe_id: str, request: RecipeSave) -> StoredRecipe:
        payload = json.dumps(
            request.recipe.model_dump(mode="json", exclude_defaults=False),
            ensure_ascii=False, separators=(",", ":"),
        )
        if len(payload) > 1048576:
            raise RecipeConflict("recipe_too_large")
        with self.database.connect(write=True) as connection:
            existing = connection.execute(
                "SELECT updated_at FROM dataset_recipes WHERE user_id = ? AND id = ?",
                (user_id, recipe_id),
            ).fetchone()
            # Strictly increasing so two quick saves never share an updated_at.
            now = max(int(time.time() * 1000), (existing["updated_at"] + 1) if existing else 0)
            if existing is None:
                if request.expected_updated_at is not None:
                    raise RecipeConflict("recipe_conflict")
                count = connection.execute(
                    "SELECT COUNT(*) FROM dataset_recipes WHERE user_id = ?", (user_id,),
                ).fetchone()[0]
                if count >= MAX_RECIPES:
                    raise RecipeConflict("recipe_limit")
                connection.execute(
                    "INSERT INTO dataset_recipes "
                    "(user_id, id, name, recipe_json, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, recipe_id, request.name, payload, now, now),
                )
            else:
                if (
                    request.expected_updated_at is not None
                    and request.expected_updated_at != existing["updated_at"]
                ):
                    raise RecipeConflict("recipe_conflict")
                connection.execute(
                    "UPDATE dataset_recipes SET name = ?, recipe_json = ?, updated_at = ? "
                    "WHERE user_id = ? AND id = ?",
                    (request.name, payload, now, user_id, recipe_id),
                )
            row = connection.execute(
                "SELECT * FROM dataset_recipes WHERE user_id = ? AND id = ?",
                (user_id, recipe_id),
            ).fetchone()
        return self._stored(row)

    def delete(self, user_id: str, recipe_id: str) -> bool:
        with self.database.connect(write=True) as connection:
            result = connection.execute(
                "DELETE FROM dataset_recipes WHERE user_id = ? AND id = ?", (user_id, recipe_id),
            )
        return result.rowcount == 1
