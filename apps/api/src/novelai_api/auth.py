"""Token issuance and revocable, database-backed browser sessions."""

import time
from uuid import uuid4

from .db import Database
from .security import SESSION_LIFETIME_SECONDS, digest_secret, new_secret


def create_token(database: Database, label: str) -> tuple[str, str]:
    label = label.strip()
    if not 1 <= len(label) <= 80 or not label.isprintable():
        raise ValueError("Label must be 1–80 printable characters")
    token = new_secret()
    user_id = str(uuid4())
    token_id = str(uuid4())
    now = int(time.time())
    with database.connect(write=True) as connection:
        connection.execute(
            "INSERT INTO users(id, label, created_at) VALUES (?, ?, ?)",
            (user_id, label, now),
        )
        connection.execute(
            "INSERT INTO access_tokens(id, user_id, token_digest, created_at) "
            "VALUES (?, ?, ?, ?)",
            (token_id, user_id, digest_secret(token), now),
        )
    return token_id, token


def list_tokens(database: Database) -> list[dict]:
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT access_tokens.id, users.label, access_tokens.created_at, "
            "access_tokens.revoked_at FROM access_tokens "
            "JOIN users ON users.id = access_tokens.user_id "
            "ORDER BY access_tokens.created_at DESC, access_tokens.id"
        ).fetchall()
    return [dict(row) for row in rows]


def revoke_token(database: Database, token_id: str) -> bool:
    now = int(time.time())
    with database.connect(write=True) as connection:
        result = connection.execute(
            "UPDATE access_tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
            (now, token_id),
        )
        if result.rowcount:
            connection.execute(
                "UPDATE browser_sessions SET revoked_at = ? "
                "WHERE token_id = ? AND revoked_at IS NULL",
                (now, token_id),
            )
        return bool(result.rowcount)


def issue_session(database: Database, token: str) -> tuple[str, dict] | None:
    now = int(time.time())
    with database.connect(write=True) as connection:
        row = connection.execute(
            "SELECT access_tokens.id AS token_id, users.id AS user_id, users.label "
            "FROM access_tokens JOIN users ON users.id = access_tokens.user_id "
            "WHERE token_digest = ? AND access_tokens.revoked_at IS NULL",
            (digest_secret(token),),
        ).fetchone()
        if row is None:
            return None
        session = new_secret()
        connection.execute(
            "INSERT INTO browser_sessions "
            "(id, user_id, token_id, session_digest, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                row["user_id"],
                row["token_id"],
                digest_secret(session),
                now,
                now + SESSION_LIFETIME_SECONDS,
            ),
        )
    return session, {"id": row["user_id"], "label": row["label"]}


def current_user(database: Database, session: str) -> dict | None:
    now = int(time.time())
    with database.connect() as connection:
        row = connection.execute(
            "SELECT users.id, users.label FROM browser_sessions "
            "JOIN access_tokens ON access_tokens.id = browser_sessions.token_id "
            "JOIN users ON users.id = browser_sessions.user_id "
            "WHERE browser_sessions.session_digest = ? "
            "AND browser_sessions.revoked_at IS NULL "
            "AND browser_sessions.expires_at > ? "
            "AND access_tokens.revoked_at IS NULL",
            (digest_secret(session), now),
        ).fetchone()
    return dict(row) if row is not None else None


def revoke_session(database: Database, session: str) -> None:
    with database.connect(write=True) as connection:
        connection.execute(
            "UPDATE browser_sessions SET revoked_at = ? "
            "WHERE session_digest = ? AND revoked_at IS NULL",
            (int(time.time()), digest_secret(session)),
        )
