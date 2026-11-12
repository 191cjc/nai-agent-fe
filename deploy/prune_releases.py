#!/usr/bin/env python3
"""Preview or remove expired immutable releases, never application data."""

import argparse
import fcntl
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

KEEP_RELEASES = 3
RELEASE_DAYS = 30
ASSET_DAYS = 365
DAY = 24 * 60 * 60
LOCK = Path("/run/lock/novelai-release-cleanup.lock")
RELEASE_NAME = re.compile(r"(\d{8}T\d{6})Z?(?:-[0-9a-f]{7,40})?\Z")
ASSET_NAME = re.compile(
    r"[A-Za-z0-9_.-]+-[A-Za-z0-9_-]{8}\."
    r"(?:js|mjs|css|map|png|jpe?g|gif|webp|avif|svg|ico|woff2?|ttf|otf|wasm)\Z"
)


@dataclass(frozen=True)
class Layout:
    # A test fixture can supply a temporary prefix; CLI paths are fixed.
    prefix: Path = Path("/")

    @property
    def api(self) -> Path:
        return self.prefix / "srv/novelai/releases"

    @property
    def web(self) -> Path:
        return self.prefix / "srv/www/novelai/releases"

    @property
    def assets(self) -> Path:
        return self.prefix / "srv/www/novelai/assets"


@dataclass(frozen=True)
class Candidate:
    path: Path
    kind: str
    identity: tuple[int, int, int, int]


@dataclass
class Plan:
    candidates: list[Candidate]
    protected: tuple[Path, Path, Path | None]
    kept: list[str]
    warnings: list[str]


def directory(path: Path) -> None:
    """Reject relative paths, traversal and symlinks in every directory component."""
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe directory: {path}")
    for component in (*reversed(path.parents), path):
        if not stat.S_ISDIR(component.lstat().st_mode):
            raise ValueError(f"Expected a real directory: {component}")


def release_time(name: str) -> float | None:
    match = RELEASE_NAME.fullmatch(name)
    if match is None:
        return None
    try:
        return datetime.strptime(match[1], "%Y%m%dT%H%M%S").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return None


def current_release(root: Path) -> Path:
    link = root.parent / "current"
    if not link.is_symlink() or ".." in link.readlink().parts:
        raise ValueError(f"Missing or unsafe current symlink: {link}")
    target = link.resolve(strict=True)
    if target.parent != root or release_time(target.name) is None:
        raise ValueError(f"Current must select a recognized direct release: {link}")
    directory(target)
    return target


def running_api_release(layout: Layout) -> Path | None:
    result = subprocess.run(
        ["systemctl", "show", "novelai-api.service", "--property=MainPID", "--value"],
        check=True, capture_output=True, text=True, timeout=10,
    )
    pid = int(result.stdout.strip())
    if pid == 0:
        return None
    if pid < 0:
        raise ValueError("Invalid API MainPID")
    cwd = Path(os.readlink(f"/proc/{pid}/cwd"))
    relative = cwd.relative_to(layout.api)
    if len(relative.parts) != 3 or relative.parts[1:] != ("apps", "api"):
        raise ValueError("Running API is outside the expected release layout")
    target = layout.api / relative.parts[0]
    directory(target)
    if release_time(target.name) is None:
        raise ValueError("Running API release has an unrecognized name")
    return target


def identity(details: os.stat_result) -> tuple[int, int, int, int]:
    return details.st_dev, details.st_ino, details.st_mtime_ns, details.st_ctime_ns


def release_candidates(
    root: Path, protected: set[Path], now: float, kind: str,
) -> tuple[list[Candidate], list[Path]]:
    recognized = []
    retained = []
    for path in sorted(root.iterdir()):
        details = path.lstat()
        timestamp = release_time(path.name)
        if timestamp is None or not stat.S_ISDIR(details.st_mode):
            retained.append(path)
            continue
        recognized.append((timestamp, path, details))
    newest = {entry[1] for entry in sorted(recognized, reverse=True)[:KEEP_RELEASES]}
    candidates = []
    for timestamp, path, details in recognized:
        newest_time = max(timestamp, details.st_mtime, details.st_ctime)
        if path in protected or path in newest or now - newest_time <= RELEASE_DAYS * DAY:
            retained.append(path)
        else:
            candidates.append(Candidate(path, kind, identity(details)))
    return candidates, retained


def referenced_assets(retained: list[Path]) -> set[str]:
    """All retained bundle members protect lazy imports, without parsing code."""
    def fail_walk(error: OSError) -> None:
        raise error

    names = set()
    for release in retained:
        directory(release)
        assets = release / "assets"
        directory(assets)
        for parent, directories, files in os.walk(assets, followlinks=False, onerror=fail_walk):
            for name in directories:
                directory(Path(parent) / name)
            for name in files:
                path = Path(parent) / name
                if not stat.S_ISREG(path.lstat().st_mode):
                    raise ValueError(f"Ambiguous retained asset: {path}")
                names.add(path.relative_to(assets).as_posix())
    return names


def make_plan(layout: Layout, now: float, running: Path | None) -> Plan:
    for root in (layout.api, layout.web, layout.assets):
        directory(root)
    api_current, web_current = current_release(layout.api), current_release(layout.web)
    if running is not None:
        if running.parent != layout.api or release_time(running.name) is None:
            raise ValueError("Running API protection is outside the release root")
        directory(running)
    protected = {api_current, web_current}
    if running is not None:
        protected.add(running)
    api_candidates, api_kept = release_candidates(layout.api, protected, now, "api_release")
    web_candidates, web_kept = release_candidates(layout.web, protected, now, "web_release")
    candidates = api_candidates + web_candidates
    warnings = []
    try:
        references = referenced_assets(web_kept)
    except (OSError, ValueError):
        # Unknown/incomplete releases must never cause an older tab's asset to disappear.
        warnings.append("Shared asset cleanup skipped: retained web references are ambiguous")
    else:
        for path in sorted(layout.assets.iterdir()):
            details = path.lstat()
            if (
                stat.S_ISREG(details.st_mode) and ASSET_NAME.fullmatch(path.name)
                and path.name not in references
                and now - max(details.st_mtime, details.st_ctime) > ASSET_DAYS * DAY
            ):
                candidates.append(Candidate(path, "asset", identity(details)))
    return Plan(
        candidates, (api_current, web_current, running),
        sorted(str(path) for path in api_kept + web_kept), warnings,
    )


def remove(candidate: Candidate) -> None:
    """Use descriptor-relative deletion; embedded symlinks are only unlinked."""
    with_fd = os.open(candidate.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        details = os.stat(candidate.path.name, dir_fd=with_fd, follow_symlinks=False)
        if identity(details) != candidate.identity:
            raise ValueError(f"Candidate changed during cleanup: {candidate.path}")
        if candidate.kind == "asset":
            if not stat.S_ISREG(details.st_mode):
                raise ValueError("Asset is no longer a regular file")
            os.unlink(candidate.path.name, dir_fd=with_fd)
        else:
            if not shutil.rmtree.avoids_symlink_attacks or not stat.S_ISDIR(details.st_mode):
                raise ValueError("Safe directory deletion is unavailable")
            shutil.rmtree(candidate.path.name, dir_fd=with_fd)
    finally:
        os.close(with_fd)


def cleanup(
    layout: Layout, *, apply: bool, now: float, running_api: Callable[[], Path | None],
) -> dict:
    plan = make_plan(layout, now, running_api())
    removed = []
    if apply:
        for candidate in plan.candidates:
            # Publishers must hold the same lock; also fail closed if pointers changed.
            latest = make_plan(layout, now, running_api())
            if latest.protected != plan.protected or candidate not in latest.candidates:
                raise ValueError("Release state changed; rerun cleanup after publication")
            remove(candidate)
            removed.append(str(candidate.path))
    return {
        "mode": "apply" if apply else "dry-run",
        "policy": {"keep_newest": KEEP_RELEASES, "release_days": RELEASE_DAYS,
                   "asset_days": ASSET_DAYS},
        "candidates": [{"kind": item.kind, "path": str(item.path)} for item in plan.candidates],
        "protected": [str(path) for path in plan.protected if path is not None],
        "kept_releases": plan.kept, "removed": removed, "warnings": plan.warnings,
    }


@contextmanager
def cleanup_lock(path: Path):
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid()
            or details.st_mode & 0o022 or details.st_nlink != 1
        ):
            raise ValueError("Cleanup lock must be owned, singly linked and not writable by others")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete the eligible previewed files")
    arguments = parser.parse_args()
    layout = Layout()
    try:
        with cleanup_lock(LOCK):
            result = cleanup(
                layout, apply=arguments.apply, now=time.time(),
                running_api=lambda: running_api_release(layout),
            )
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Release cleanup refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
