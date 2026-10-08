"""Operator-only token administration; never exposes these routes over HTTP."""

import argparse
import json
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
    elif arguments.command == "revoke":
        if not revoke_token(database, arguments.token_id):
            parser.error("Token not found or already revoked")
        print("Token revoked")


if __name__ == "__main__":
    main()
