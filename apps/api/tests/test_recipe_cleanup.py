"""Operator recipe reset uses only disposable SQLite and invented sentinel data."""

import json
import sqlite3
from pathlib import Path

import pytest

from novelai_api.admin import main as admin_main
from novelai_api.config import Settings
from novelai_api.dataset_recipes import RecipeStore
from novelai_api.db import Database


@pytest.fixture
def database(tmp_path: Path) -> Database:
    instance = Database(tmp_path / "synthetic" / "workspace.sqlite3")
    instance.migrate()
    with instance.connect(write=True) as connection:
        for owner in ("alice", "bob"):
            connection.execute("INSERT INTO users VALUES (?, ?, 1)", (owner, owner))
            connection.execute(
                "INSERT INTO access_tokens VALUES (?, ?, ?, 1, NULL)",
                (f"token-{owner}", owner, f"synthetic-digest-{owner}"),
            )
            for index in range(2):
                connection.execute(
                    "INSERT INTO dataset_recipes VALUES (?, ?, ?, ?, 1, 1)",
                    (owner, f"recipe-{owner}-{index}", f"synthetic-name-{owner}-{index}",
                     "not-json-synthetic-recipe-sentinel"),
                )
            connection.execute(
                "INSERT INTO generation_jobs "
                "(id, user_id, positive_prompt, negative_prompt, settings_json, "
                "effective_seed, status, created_at, updated_at) "
                "VALUES (?, ?, 'synthetic content', '', '{}', 1, 'succeeded', 1, 1)",
                (f"job-{owner}", owner),
            )
            for kind in ("style", "dataset", "character"):
                definition = json.dumps({"kind": kind, "fixture": "frozen synthetic item"})
                connection.execute(
                    "INSERT INTO style_experiment_runs "
                    "(user_id, id, definition_json, total, seed, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, '1', 1, 'completed', 1, 1)",
                    (owner, f"run-{owner}-{kind}", definition),
                )
            connection.execute(
                "INSERT INTO prompt_snapshots VALUES (?, ?, ?, ?, 1)",
                (owner, f"snapshot-{owner}", "synthetic snapshot", '["synthetic prompt"]'),
            )
    return instance


def retained_records(database: Database) -> dict[str, list[tuple]]:
    """Snapshot only this test's invented records, never a configured database."""
    with database.connect() as connection:
        return {
            table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table}")]
            for table in (
                "users", "access_tokens", "generation_jobs", "style_experiment_runs",
                "prompt_snapshots",
            )
        }


def recipe_count(database: Database) -> int:
    with database.connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM dataset_recipes").fetchone()[0]


def test_reset_clears_every_owner_without_decoding_and_preserves_other_data(
    database: Database,
) -> None:
    retained = retained_records(database)
    synthetic_image = database.path.parent / "generation-images" / "synthetic.keep"
    synthetic_image.parent.mkdir()
    synthetic_image.write_bytes(b"invented image fixture")
    store = RecipeStore(database)

    assert store.clear_all() == 4
    assert recipe_count(database) == 0
    assert retained_records(database) == retained
    assert synthetic_image.is_file()
    assert store.clear_all() == 0
    assert retained_records(database) == retained


def test_reset_rolls_back_if_any_recipe_delete_fails(database: Database) -> None:
    with database.connect(write=True) as connection:
        connection.execute(
            "CREATE TRIGGER synthetic_reject_delete BEFORE DELETE ON dataset_recipes "
            "WHEN OLD.id = 'recipe-bob-1' "
            "BEGIN SELECT RAISE(ABORT, 'synthetic delete failure'); END",
        )

    with pytest.raises(sqlite3.IntegrityError, match="synthetic delete failure"):
        RecipeStore(database).clear_all()
    assert recipe_count(database) == 4


def test_reset_cli_requires_explicit_all_users_before_loading_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    def reject_settings():
        raise AssertionError("A rejected command must not access configuration or SQLite")

    monkeypatch.setattr(Settings, "from_env", reject_settings)
    monkeypatch.setattr("sys.argv", ["novelai-admin", "clear-dataset-recipes"])
    with pytest.raises(SystemExit) as failure:
        admin_main()
    assert failure.value.code == 2
    printed = capsys.readouterr()
    assert printed.out == ""
    assert "--all-users" in printed.err


def test_reset_cli_prints_only_deleted_count_and_is_repeatable(
    database: Database, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    retained = retained_records(database)
    monkeypatch.setattr(Settings, "from_env", lambda: Settings(
        database.path, "https://synthetic.invalid",
    ))
    monkeypatch.setattr("sys.argv", ["novelai-admin", "clear-dataset-recipes", "--all-users"])

    admin_main()
    printed = capsys.readouterr()
    assert printed.out == '{"deleted_recipes": 4}\n'
    assert printed.err == ""
    assert recipe_count(database) == 0
    assert retained_records(database) == retained

    admin_main()
    assert capsys.readouterr().out == '{"deleted_recipes": 0}\n'
