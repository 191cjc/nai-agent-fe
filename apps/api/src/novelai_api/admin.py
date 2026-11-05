"""Operator-only token administration; never exposes these routes over HTTP."""

import argparse
import json
import uuid
from pathlib import Path

from .auth import create_token, list_tokens, revoke_token
from .config import Settings
from .db import Database


def main() -> None:
    parser = argparse.ArgumentParser(prog="novelai-admin")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="Create/upgrade local SQLite schema")
    backup = commands.add_parser("backup", help="Create a consistent SQLite backup")
    backup.add_argument("output", type=Path)
    create = commands.add_parser("create", help="Issue an access token for one user")
    create.add_argument("--label", required=True)
    commands.add_parser("list", help="List token metadata without secrets")
    revoke = commands.add_parser("revoke", help="Invalidate an issued token and its sessions")
    revoke.add_argument("token_id")
    proceed = commands.add_parser(
        "continue-run", help="Create the continuation of a stopped dataset run (ids only)",
    )
    proceed.add_argument("run_id")
    arguments = parser.parse_args()
    database = Database(Settings.from_env().sqlite_path)

    if arguments.command == "migrate":
        database.migrate()
        print("SQLite schema ready")
    elif arguments.command == "backup":
        database.backup(arguments.output)
        print("SQLite backup verified")
    elif arguments.command == "create":
        token_id, token = create_token(database, arguments.label)
        print(f"Token ID: {token_id}\nAccess token (shown once): {token}")
    elif arguments.command == "list":
        print(json.dumps(list_tokens(database), ensure_ascii=False))
    elif arguments.command == "continue-run":
        # Copies the stored definition server-side; prints only ids and counts.
        from .reference_images import ReferenceImageStore
        from .style_experiments import ContinuationRefused, RunStore

        settings = Settings.from_env()
        with database.connect() as connection:
            row = connection.execute(
                "SELECT user_id FROM style_experiment_runs WHERE id = ?", (arguments.run_id,),
            ).fetchone()
        if row is None:
            parser.error("Run not found")
        images = ReferenceImageStore(database)

        def digest(user_id: str, reference_id: str) -> str | None:
            item = images.get(user_id, reference_id)
            return item.sha256 if item is not None else None

        try:
            created = RunStore(database).continue_run(
                row["user_id"], arguments.run_id, uuid.uuid4(), digest,
                gpt_model=settings.gpt_image_model,
            )
        except ContinuationRefused as exception:
            parser.error(f"Cannot continue: {exception.code}")
        print(json.dumps({
            "id": created.id, "lane": created.lane, "total": created.total,
            "queue_position": created.queue_position,
        }))
    elif arguments.command == "revoke":
        if not revoke_token(database, arguments.token_id):
            parser.error("Token not found or already revoked")
        print("Token revoked")


if __name__ == "__main__":
    main()
