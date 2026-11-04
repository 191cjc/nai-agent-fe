"""Private bounded seven-day image files, independent of code releases and SQLite."""

import hashlib
import json
import os
import shutil
import stat
import threading
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from .generations import (
    MAX_IMAGE_BYTES,
    MAX_RESULT_BYTES,
    CachedResult,
    GeneratedImage,
    ResultInfo,
    ResultStorageUnavailable,
    valid_images,
)

IMAGE_RETENTION_SECONDS = 7 * 24 * 60 * 60
# No fixed store budget by default: admission stops only when free disk would drop
# below the reserve. Tests may still pass an explicit budget.
IMAGE_BUDGET_BYTES: int | None = None
FREE_DISK_RESERVE_BYTES = 3 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 8192
DIRECTORY_OVERHEAD_BYTES = 64 * 1024
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def _uuid(value: str) -> bool:
    try:
        return str(UUID(value)) == value
    except (ValueError, TypeError, AttributeError):
        return False


def _disk_free(path: Path) -> int:
    return shutil.disk_usage(path).free


def _artifact(name: str, prefix: str) -> bool:
    return name.startswith(prefix) and _uuid(name[len(prefix):])


class DiskResultStore:
    def __init__(
        self, path: Path, *, clock: Callable[[], float] = time.time,
        disk_free: Callable[[Path], int] = _disk_free,
        budget_bytes: int | None = IMAGE_BUDGET_BYTES,
        free_reserve_bytes: int = FREE_DISK_RESERVE_BYTES,
        sweep_interval: float = 60,
    ):
        # Do not mkdir/open here: constructing OpenAPI must have no side effects.
        self.path = path
        self._clock = clock
        self._disk_free = disk_free
        self._budget = budget_bytes
        self._free_reserve = free_reserve_bytes
        self._sweep_interval = sweep_interval
        self._lock = threading.Lock()
        self._reservations: dict[str, int] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @contextmanager
    def _root(self, *, create: bool = False):
        if create:
            self.path.mkdir(mode=0o700, exist_ok=True)
        descriptor = os.open(self.path, DIRECTORY_FLAGS)
        try:
            if os.name == "posix":
                os.fchmod(descriptor, 0o700)
            yield descriptor
        finally:
            os.close(descriptor)

    def start(self) -> None:
        with self._lock:
            try:
                with self._root(create=True) as root:
                    self._sweep(root, startup=True)
            except (OSError, ResultStorageUnavailable):
                # Keep parameter history/readiness available; admission safely refuses.
                pass
            if self._thread is not None:
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._clean_loop, name="nai-image-cleanup", daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=max(1, min(self._sweep_interval, 5)))
        self._thread = None
        with self._lock:
            self._reservations.clear()

    def _clean_loop(self) -> None:
        while not self._stop.wait(self._sweep_interval):
            self.sweep()

    def sweep(self) -> None:
        with self._lock:
            try:
                with self._root() as root:
                    self._sweep(root)
            except (OSError, ResultStorageUnavailable):
                pass

    def reserve(self, sample_count: int) -> str:
        amount = min(sample_count * MAX_IMAGE_BYTES, MAX_RESULT_BYTES) + DIRECTORY_OVERHEAD_BYTES
        with self._lock:
            try:
                with self._root(create=True) as root:
                    used = self._sweep(root)
                    pending = sum(self._reservations.values())
                    if (
                        (self._budget is not None and used + pending + amount > self._budget)
                        or self._disk_free(self.path) - pending - amount < self._free_reserve
                    ):
                        raise ResultStorageUnavailable("Image storage has no capacity")
                    # Exercise exclusive creation, writing and fsync before paid admission.
                    name = f".reserve-{uuid4()}"
                    descriptor = os.open(
                        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600, dir_fd=root,
                    )
                    try:
                        self._write(descriptor, b"storage-preflight")
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                        os.unlink(name, dir_fd=root)
                    reservation = str(uuid4())
                    self._reservations[reservation] = amount
                    return reservation
            except OSError as exception:
                raise ResultStorageUnavailable("Image storage unavailable") from exception

    def release(self, reservation: str) -> None:
        with self._lock:
            self._reservations.pop(reservation, None)

    @staticmethod
    def _write(descriptor: int, data: bytes) -> None:
        remaining = memoryview(data)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("Image write failed")
            remaining = remaining[written:]

    @staticmethod
    def _read(directory: int, name: str, maximum: int) -> bytes:
        descriptor = os.open(name, FILE_FLAGS, dir_fd=directory)
        try:
            details = os.fstat(descriptor)
            if not stat.S_ISREG(details.st_mode) or not 0 < details.st_size <= maximum:
                raise ValueError("Invalid image file")
            chunks = bytearray()
            while len(chunks) <= maximum:
                chunk = os.read(descriptor, min(65536, maximum + 1 - len(chunks)))
                if not chunk:
                    break
                chunks.extend(chunk)
            if len(chunks) != details.st_size or len(chunks) > maximum:
                raise ValueError("Invalid image size")
            return bytes(chunks)
        finally:
            os.close(descriptor)

    def put(self, job_id: str, user_id: str, images: Sequence[GeneratedImage]) -> bool:
        if not _uuid(job_id) or not _uuid(user_id) or not valid_images(images):
            return False
        saved_at = int(self._clock())
        manifest = {
            "version": 1, "job_id": job_id, "user_id": user_id, "saved_at": saved_at,
            "expires_at": saved_at + IMAGE_RETENTION_SECONDS,
            "images": [{"size": len(image.data), "sha256": hashlib.sha256(image.data).hexdigest()}
                       for image in images],
        }
        serialized = json.dumps(manifest, separators=(",", ":")).encode("utf-8")
        with self._lock:
            try:
                with self._root(create=True) as root:
                    size = sum(len(image.data) for image in images) + DIRECTORY_OVERHEAD_BYTES
                    if (
                        (self._budget is not None and self._sweep(root) + size > self._budget)
                        or self._disk_free(self.path) - size < self._free_reserve
                    ):
                        raise OSError("Image storage has no capacity")
                    temporary = f".tmp-{uuid4()}"
                    os.mkdir(temporary, mode=0o700, dir_fd=root)
                    directory = os.open(temporary, DIRECTORY_FLAGS, dir_fd=root)
                    try:
                        contents = [image.data for image in images] + [serialized]
                        for index, data in enumerate(contents):
                            name = f"{index}.png" if index < len(images) else "manifest.json"
                            descriptor = os.open(
                                name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                0o600, dir_fd=directory,
                            )
                            try:
                                self._write(descriptor, data)
                                os.fsync(descriptor)
                            finally:
                                os.close(descriptor)
                        os.fsync(directory)
                    finally:
                        os.close(directory)
                    try:
                        os.stat(job_id, dir_fd=root, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise OSError("Image result already exists")
                    os.rename(temporary, job_id, src_dir_fd=root, dst_dir_fd=root)
                    os.fsync(root)
                return True
            except OSError as exception:
                try:
                    with self._root() as root:
                        if "temporary" in locals():
                            self._remove_directory(root, temporary)
                except OSError:
                    pass
                raise ResultStorageUnavailable("Image result could not be saved") from exception

    def _manifest(self, directory: int, job_id: str) -> dict:
        manifest = json.loads(self._read(directory, "manifest.json", MAX_MANIFEST_BYTES))
        if (
            not isinstance(manifest, dict) or manifest.get("version") != 1
            or manifest.get("job_id") != job_id or not _uuid(manifest.get("user_id"))
            or type(manifest.get("saved_at")) is not int or manifest["saved_at"] < 0
            or type(manifest.get("expires_at")) is not int
            or manifest["expires_at"] != manifest["saved_at"] + IMAGE_RETENTION_SECONDS
            or not isinstance(manifest.get("images"), list)
            or not 1 <= len(manifest["images"]) <= 8
        ):
            raise ValueError("Invalid image manifest")
        total = 0
        for image in manifest["images"]:
            if (
                not isinstance(image, dict) or type(image.get("size")) is not int
                or not 45 <= image["size"] <= MAX_IMAGE_BYTES
                or not isinstance(image.get("sha256"), str) or len(image["sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in image["sha256"])
            ):
                raise ValueError("Invalid image manifest")
            total += image["size"]
        if total > MAX_RESULT_BYTES:
            raise ValueError("Invalid image result size")
        return manifest

    @contextmanager
    def _result(self, job_id: str, user_id: str):
        if not _uuid(job_id) or not _uuid(user_id):
            raise ValueError("Invalid image identity")
        with self._root() as root:
            directory = os.open(job_id, DIRECTORY_FLAGS, dir_fd=root)
            try:
                manifest = self._manifest(directory, job_id)
                if manifest["user_id"] != user_id or self._clock() >= manifest["expires_at"]:
                    raise ValueError("Image unavailable")
                # A missing/symlink/short/oversized member invalidates the entire set.
                for index, image in enumerate(manifest["images"]):
                    details = os.stat(f"{index}.png", dir_fd=directory, follow_symlinks=False)
                    if not stat.S_ISREG(details.st_mode) or details.st_size != image["size"]:
                        raise ValueError("Image unavailable")
                yield directory, manifest
            finally:
                os.close(directory)

    # Reads take no lock: results appear by atomic rename and are never modified in place,
    # so a concurrent sweep/discard can only make a read fail closed (None).
    def describe(self, job_id: str, user_id: str) -> ResultInfo | None:
        try:
            with self._result(job_id, user_id) as (_directory, manifest):
                return ResultInfo(len(manifest["images"]), manifest["expires_at"])
        except (OSError, ValueError, TypeError):
            return None

    def image(self, job_id: str, user_id: str, index: int) -> GeneratedImage | None:
        try:
            with self._result(job_id, user_id) as (directory, manifest):
                if not 0 <= index < len(manifest["images"]):
                    return None
                data = self._read(directory, f"{index}.png", MAX_IMAGE_BYTES)
                image = GeneratedImage(data, "image/png")
                if (
                    hashlib.sha256(data).hexdigest() != manifest["images"][index]["sha256"]
                    or not valid_images([image])
                ):
                    return None
                return image
        except (OSError, ValueError, TypeError):
            return None

    def get(self, job_id: str, user_id: str) -> CachedResult | None:
        """Compatibility helper; routes use metadata and one selected image instead."""
        info = self.describe(job_id, user_id)
        if info is None:
            return None
        images = tuple(self.image(job_id, user_id, index) for index in range(info.image_count))
        if any(image is None for image in images):
            return None
        return CachedResult(
            user_id, images, info.expires_at, float(info.expires_at),
            sum(len(image.data) for image in images),
        )

    def discard(self, job_id: str) -> None:
        if not _uuid(job_id):
            return
        with self._lock:
            try:
                with self._root() as root:
                    self._remove_directory(root, job_id)
            except OSError:
                pass

    @staticmethod
    def _remove_directory(root: int, name: str) -> None:
        # Never recurse through a link or an unexpected nested directory.
        directory = os.open(name, DIRECTORY_FLAGS, dir_fd=root)
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        os.unlink(entry.name, dir_fd=directory)
        finally:
            os.close(directory)
        os.rmdir(name, dir_fd=root)

    def _sweep(self, root: int, *, startup: bool = False) -> int:
        size = 0
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    details = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(details.st_mode):
                        directory = os.open(entry.name, DIRECTORY_FLAGS, dir_fd=root)
                        try:
                            expiry = details.st_mtime + IMAGE_RETENTION_SECONDS
                            temporary = _artifact(entry.name, ".tmp-")
                            if temporary:
                                expiry = details.st_mtime + 60 * 60
                            if _uuid(entry.name):
                                try:
                                    expiry = self._manifest(directory, entry.name)["expires_at"]
                                except (OSError, ValueError, TypeError):
                                    pass
                            if (
                                (_uuid(entry.name) or temporary)
                                and ((temporary and startup)
                                     or self._clock() >= expiry)
                            ):
                                os.close(directory)
                                directory = None
                                self._remove_directory(root, entry.name)
                                continue
                            size += DIRECTORY_OVERHEAD_BYTES
                            with os.scandir(directory) as members:
                                for member in members:
                                    info = member.stat(follow_symlinks=False)
                                    if stat.S_ISDIR(info.st_mode):
                                        # Unknown nested trees cannot be safely budgeted.
                                        raise ResultStorageUnavailable("Invalid image storage")
                                    size += info.st_size
                        finally:
                            if directory is not None:
                                os.close(directory)
                    elif _artifact(entry.name, ".reserve-") and (
                        startup or self._clock() >= details.st_mtime + 60 * 60
                    ):
                        os.unlink(entry.name, dir_fd=root)
                    else:
                        size += details.st_size + DIRECTORY_OVERHEAD_BYTES
                except FileNotFoundError:
                    continue
        return size
