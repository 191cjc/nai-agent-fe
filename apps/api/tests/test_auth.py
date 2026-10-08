"""Only temporary SQLite files and in-process HTTP; no paid providers or network."""

import json
import os
import sqlite3
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from novelai_api.admin import main as admin_main
from novelai_api.app import create_app
from novelai_api.auth import create_token, list_tokens, revoke_token
from novelai_api.config import Settings
from novelai_api.db import Database
from novelai_api.security import SESSION_COOKIE, SESSION_LIFETIME_SECONDS, digest_secret


@pytest.fixture
def database(tmp_path: Path) -> Database:
    instance = Database(tmp_path / "private" / "workspace.sqlite3")
    instance.migrate()
    return instance


@pytest.fixture
def client(database: Database) -> TestClient:
    with TestClient(
        create_app(Settings(database.path, "https://testserver"), database),
        base_url="https://testserver",
    ) as test_client:
        yield test_client


def login(client: TestClient, token: str):
    return client.post(
        "/api/auth/session", json={"token": token}, headers={"Origin": "https://testserver"}
    )


def test_admin_issues_only_hash_and_never_lists_token(database: Database) -> None:
    token_id, secret = create_token(database, "alice")
    metadata = list_tokens(database)
    assert len(metadata) == 1
    assert metadata[0]["id"] == token_id
    assert secret not in repr(metadata)
    with database.connect() as connection:
        digest = connection.execute("SELECT token_digest FROM access_tokens").fetchone()[0]
        assert digest == digest_secret(secret)
        assert secret not in "\n".join(connection.iterdump())


def test_token_exchange_cookie_reload_and_logout(client: TestClient, database: Database) -> None:
    _token_id, token = create_token(database, "alice")
    response = login(client, token)
    assert response.status_code == 200
    assert response.json()["label"] == "alice"
    cookie = response.headers["set-cookie"]
    assert SESSION_COOKIE in cookie
    assert "httponly" in cookie.lower()
    assert "secure" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert f"Max-Age={SESSION_LIFETIME_SECONDS}" in cookie
    assert "Cache-Control" in response.headers
    assert client.get("/api/auth/session").status_code == 200

    old_session = client.cookies.get(SESSION_COOKIE)
    response = client.delete("/api/auth/session", headers={"Origin": "https://testserver"})
    assert response.status_code == 204
    assert client.get("/api/auth/session").status_code == 401
    client.cookies.set(SESSION_COOKIE, old_session)
    assert client.get("/api/auth/session").status_code == 401


def test_restart_keeps_session_but_revoke_disables_it(database: Database) -> None:
    token_id, token = create_token(database, "alice")
    settings = Settings(database.path, "https://testserver")
    with TestClient(create_app(settings, database), base_url="https://testserver") as first:
        assert login(first, token).status_code == 200
        session = first.cookies.get(SESSION_COOKIE)
    assert session
    with TestClient(
        create_app(settings, Database(database.path)), base_url="https://testserver"
    ) as restarted:
        restarted.cookies.set(SESSION_COOKIE, session)
        assert restarted.get("/api/auth/session").status_code == 200
        assert revoke_token(database, token_id)
        assert restarted.get("/api/auth/session").status_code == 401
        assert login(restarted, token).status_code == 401
        assert not revoke_token(database, token_id)


def test_two_users_and_invalid_login(client: TestClient, database: Database) -> None:
    _alice_id, alice_token = create_token(database, "alice")
    _bob_id, bob_token = create_token(database, "bob")
    assert login(client, "wrong").json() == {
        "code": "invalid_token",
        "message": "Invalid access token",
        "retryable": False,
    }
    assert login(client, alice_token).json()["label"] == "alice"
    alice_session = client.cookies.get(SESSION_COOKIE)
    assert login(client, bob_token).json()["label"] == "bob"
    assert client.get("/api/auth/session").json()["label"] == "bob"
    client.cookies.set(SESSION_COOKIE, alice_session)
    assert client.get("/api/auth/session").json()["label"] == "alice"


def test_invalid_origin_rejected_before_token_lookup(
    client: TestClient, database: Database
) -> None:
    _token_id, token = create_token(database, "alice")
    assert client.post("/api/auth/session", json={"token": token}).status_code == 403
    assert login(client, token).status_code == 200
    assert client.delete(
        "/api/auth/session", headers={"Origin": "https://attacker.example"}
    ).status_code == 403
    assert client.get("/api/auth/session").status_code == 200


def test_validation_does_not_echo_token(client: TestClient) -> None:
    token = "private-token-example"
    response = client.post(
        "/api/auth/session", json={"token": token * 100}, headers={"Origin": "https://testserver"}
    )
    assert response.status_code == 422
    assert token not in response.text
    assert response.json()["code"] == "validation_error"


def test_openapi_never_exposes_server_credentials_or_admin_commands(database: Database) -> None:
    secret = "private-mcp-token-fixture"
    settings = Settings(
        database.path,
        "https://testserver",
        novelai_mcp_token=secret,
    )
    schema = create_app(settings, database).openapi()
    serialized = json.dumps(schema)
    assert secret not in serialized
    assert "NAI_NOVELAI_MCP_TOKEN" not in serialized
    assert all(not path.startswith("/api/admin") for path in schema["paths"])


def test_login_limiter_rejects_sixth_attempt(client: TestClient) -> None:
    for _attempt in range(5):
        assert login(client, "invalid").status_code == 401
    assert login(client, "invalid").status_code == 429


def test_expired_session_returns_401(client: TestClient, database: Database) -> None:
    _token_id, token = create_token(database, "alice")
    assert login(client, token).status_code == 200
    with database.connect(write=True) as connection:
        connection.execute("UPDATE browser_sessions SET expires_at = ?", (int(time.time()) - 1,))
    assert client.get("/api/auth/session").status_code == 401


def test_migration_is_idempotent_and_readiness_requires_it(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.sqlite3")
    with TestClient(
        create_app(Settings(database.path, "https://testserver"), database),
        base_url="https://testserver",
    ) as client:
        assert client.get("/api/health/live").status_code == 200
        assert client.get("/api/health/ready").status_code == 503
        assert not database.path.exists()
        database.migrate()
        database.migrate()
        assert client.get("/api/health/ready").status_code == 200
        with database.connect(write=True) as connection:
            connection.execute("PRAGMA user_version = 99")
        assert client.get("/api/health/ready").status_code == 503
        with pytest.raises(RuntimeError, match="Unsupported SQLite schema version"):
            database.migrate()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_new_database_and_directories_are_private_with_permissive_umask(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir(mode=0o755)
    existing.chmod(0o755)
    path = existing / "data" / "nested" / "workspace.sqlite3"
    initial_backup = existing / "initial-snapshot.sqlite3"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys; from pathlib import Path; "
            "from novelai_api.db import Database; os.umask(0); "
            "database = Database(Path(sys.argv[1])); database.migrate(); "
            "database.backup(Path(sys.argv[2]))",
            str(path),
            str(initial_backup),
        ],
        check=True,
    )
    assert stat.S_IMODE(existing.stat().st_mode) == 0o755
    assert stat.S_IMODE(path.parent.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(initial_backup.stat().st_mode) == 0o600

    database = Database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO users VALUES ('alice', 'alice', 1)")
        connection.commit()
        for suffix in ("-wal", "-shm"):
            assert stat.S_IMODE(Path(f"{path}{suffix}").stat().st_mode) == 0o600
        target = existing / "snapshot.sqlite3"
        database.backup(target)
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
        with sqlite3.connect(target) as snapshot:
            assert snapshot.execute("SELECT label FROM users").fetchone()[0] == "alice"


@pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")
def test_v1_migration_restricts_existing_files_and_preserves_auth(tmp_path: Path) -> None:
    directory = tmp_path / "existing"
    directory.mkdir()
    directory.chmod(0o755)
    path = directory / "workspace.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            files("novelai_api").joinpath("migrations", "0001_auth.sql").read_text()
        )
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("INSERT INTO users VALUES ('alice', 'alice', 1)")
        connection.execute(
            "INSERT INTO access_tokens VALUES ('token', 'alice', 'private-digest', 1, NULL)"
        )
        connection.execute(
            "INSERT INTO browser_sessions VALUES "
            "('session', 'alice', 'token', 'session-digest', 1, 9999999999, NULL)"
        )
        connection.commit()
        for file_path in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
            file_path.chmod(0o777)

        database = Database(path)
        database.migrate()
        database.migrate()
        assert stat.S_IMODE(directory.stat().st_mode) == 0o755
        for file_path in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
            assert stat.S_IMODE(file_path.stat().st_mode) == 0o600
        with database.connect() as migrated:
            assert migrated.execute("PRAGMA user_version").fetchone()[0] == 2
            assert migrated.execute("SELECT token_digest FROM access_tokens").fetchone()[0] == (
                "private-digest"
            )
            assert migrated.execute("SELECT session_digest FROM browser_sessions").fetchone()[0] == (
                "session-digest"
            )
            assert migrated.execute("SELECT label FROM users").fetchone()[0] == "alice"


@pytest.mark.skipif(os.name != "posix", reason="POSIX symlink behavior")
def test_backup_rejects_dangling_symlink(database: Database, tmp_path: Path) -> None:
    target = tmp_path / "unexpected.sqlite3"
    link = tmp_path / "backup.sqlite3"
    link.symlink_to(target)

    with pytest.raises(FileExistsError):
        database.backup(link)

    assert link.is_symlink()
    assert not target.exists()


def test_backup_failure_closes_snapshot_and_removes_file(
    database: Database, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshots: list[sqlite3.Connection] = []

    class FailingSource:
        def backup(self, snapshot: sqlite3.Connection) -> None:
            snapshots.append(snapshot)
            raise RuntimeError("interrupted backup")

    @contextmanager
    def failing_connect():
        yield FailingSource()

    monkeypatch.setattr(database, "connect", failing_connect)
    destination = tmp_path / "interrupted.sqlite3"
    with pytest.raises(RuntimeError, match="interrupted backup"):
        database.backup(destination)

    assert not destination.exists()
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        snapshots[0].execute("SELECT 1")


def test_admin_command_never_reprints_token(
    database: Database, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("NAI_SQLITE_PATH", str(database.path))
    monkeypatch.setenv("NAI_PUBLIC_ORIGIN", "https://testserver")
    monkeypatch.setattr("sys.argv", ["novelai-admin", "create", "--label", "alice"])
    admin_main()
    printed = capsys.readouterr().out
    token = printed.split("Access token (shown once): ")[1].strip()
    token_id = printed.split("Token ID: ")[1].splitlines()[0]
    monkeypatch.setattr("sys.argv", ["novelai-admin", "list"])
    admin_main()
    assert token not in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["novelai-admin", "revoke", token_id])
    admin_main()
    assert token not in capsys.readouterr().out


def test_no_secret_columns_in_users(database: Database) -> None:
    with database.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    assert "token" not in columns
    assert "session" not in columns


def test_config_rejects_urls_and_origins_with_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NAI_SQLITE_PATH", "sqlite:///workspace.sqlite3")
    with pytest.raises(ValueError, match="file path"):
        Settings.from_env()
    monkeypatch.setenv("NAI_SQLITE_PATH", "./workspace.sqlite3")
    monkeypatch.setenv("NAI_PUBLIC_ORIGIN", "https://example.test/api")
    with pytest.raises(ValueError, match="exact HTTPS origin"):
        Settings.from_env()
    monkeypatch.setenv("NAI_PUBLIC_ORIGIN", "https://example.test")
    monkeypatch.setenv("NAI_DANBOORU_SEARCH_API_URL", "http://search.example/api")
    with pytest.raises(ValueError, match="HTTPS API base URL"):
        Settings.from_env()
    monkeypatch.setenv("NAI_DANBOORU_SEARCH_API_URL", "https://search.example/api")
    monkeypatch.setenv("NAI_NOVELAI_MCP_URL", "http://mcp.example/mcp")
    with pytest.raises(ValueError, match="HTTPS MCP endpoint"):
        Settings.from_env()
