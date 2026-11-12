"""Explicit, versioned migrations and short-lived SQLite connections."""

import os
import sqlite3
import stat
from collections.abc import Iterator
from contextlib import closing, contextmanager
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote

SCHEMA_VERSION = 14


def _restrict_existing_file(path: Path, *, missing_ok: bool = False) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        if missing_ok:
            return
        raise
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise OSError(f"SQLite path is not a regular file: {path}")
        if os.name == "posix":
            mode = stat.S_IMODE(file_stat.st_mode)
            restricted_mode = mode & 0o600
            if mode != restricted_mode:
                os.fchmod(descriptor, restricted_mode)
    finally:
        os.close(descriptor)


class Database:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()

    @contextmanager
    def connect(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        uri = f"file:{quote(str(self.path), safe='/')}?mode=rw"
        connection = sqlite3.connect(uri, uri=True, timeout=5, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            if write:
                connection.commit()
        except BaseException:
            if write:
                connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        for directory in reversed((self.path.parent, *self.path.parent.parents)):
            directory.mkdir(mode=0o700, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            _restrict_existing_file(self.path)
        else:
            os.close(descriptor)
        for suffix in ("-wal", "-shm"):
            _restrict_existing_file(Path(f"{self.path}{suffix}"), missing_ok=True)
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA foreign_keys = ON")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(f"Unsupported SQLite schema version: {version}")
            for next_version, filename in (
                (1, "0001_auth.sql"),
                (2, "0002_generations.sql"),
                (3, "0003_style_experiments.sql"),
                (4, "0004_prompt_snapshots.sql"),
                (5, "0005_provider_requests.sql"),
                (6, "0006_reference_images.sql"),
                (7, "0007_discarded_images.sql"),
                (8, "0008_experiment_names.sql"),
                (9, "0009_run_queue.sql"),
                (10, "0010_run_inflight.sql"),
                (11, "0011_run_parallelism.sql"),
                (12, "0012_caption_overrides.sql"),
                (13, "0013_purged_images.sql"),
                (14, "0014_dataset_recipes.sql"),
            ):
                if version >= next_version:
                    continue
                script = files("novelai_api").joinpath("migrations", filename).read_text()
                try:
                    connection.executescript(script)
                except BaseException:
                    connection.rollback()
                    raise
                version = next_version
            connection.execute("PRAGMA journal_mode = WAL")
        finally:
            connection.close()

    def check_ready(self) -> bool:
        try:
            with self.connect(write=True) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version != SCHEMA_VERSION:
                    return False
                connection.execute("SELECT 1 FROM access_tokens LIMIT 1")
                connection.execute("SELECT provider_request_json FROM generation_jobs LIMIT 1")
                connection.execute("SELECT 1 FROM style_experiment_runs LIMIT 1")
                connection.execute("SELECT 1 FROM prompt_snapshots LIMIT 1")
                connection.execute("SELECT 1 FROM reference_images LIMIT 1")
                connection.execute("SELECT 1 FROM discarded_images LIMIT 1")
                connection.execute("SELECT 1 FROM experiment_names LIMIT 1")
                connection.execute("SELECT lane FROM style_experiment_runs LIMIT 1")
                connection.execute("SELECT 1 FROM style_experiment_inflight LIMIT 1")
                connection.execute("SELECT parallelism FROM style_experiment_runs LIMIT 1")
                connection.execute("SELECT 1 FROM caption_overrides LIMIT 1")
                connection.execute("SELECT completed_at FROM purged_images LIMIT 1")
                connection.execute("SELECT 1 FROM dataset_recipes LIMIT 1")
            return True
        except (sqlite3.Error, OSError):
            return False

    def backup(self, destination: Path) -> None:
        destination = destination.expanduser().absolute()
        if destination == self.path:
            raise ValueError("Backup destination must differ from the live database")
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        try:
            with self.connect() as source:
                with closing(sqlite3.connect(destination)) as snapshot:
                    source.backup(snapshot)
                    result = snapshot.execute("PRAGMA integrity_check").fetchone()[0]
                    if result != "ok":
                        raise RuntimeError("SQLite backup integrity check failed")
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
