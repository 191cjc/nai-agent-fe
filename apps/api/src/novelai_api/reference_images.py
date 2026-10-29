"""Owner-private reference images for character dataset runs (disk bytes, SQLite metadata)."""

import hashlib
import json
import os
import stat
import struct
import time
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel

from .db import Database

MAX_REFERENCE_BYTES = 8 * 1024 * 1024
MAX_REFERENCE_SIDE = 2048
MIN_REFERENCE_SIDE = 64
MAX_REFERENCES_PER_OWNER = 20
MAX_REFERENCE_BYTES_PER_OWNER = 128 * 1024 * 1024
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_FRAME_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)


class ReferenceImage(BaseModel):
    id: str
    sha256: str
    mime_type: Literal["image/png", "image/jpeg"]
    width: int
    height: int
    byte_size: int
    source: Literal["upload", "result"]
    created_at: int


class ReferenceImageList(BaseModel):
    items: list[ReferenceImage]


class ReferenceFailure(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            return None
        marker = data[index + 1]
        if marker == 0xFF:
            index += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            index += 2
            continue
        length = struct.unpack(">H", data[index + 2:index + 4])[0]
        if length < 2 or index + 2 + length > len(data):
            return None
        if marker in JPEG_FRAME_MARKERS and length >= 7:
            height, width = struct.unpack(">HH", data[index + 5:index + 9])
            return width, height
        if marker == 0xDA:
            return None
        index += 2 + length
    return None


def inspect_image(data: bytes) -> tuple[str, int, int]:
    """Verify format by header only (no decoder dependency) and return mime and size."""
    if not 0 < len(data) <= MAX_REFERENCE_BYTES:
        raise ReferenceFailure(413, "reference_too_large", "Reference image exceeds 8 MiB")
    if data.startswith(PNG_SIGNATURE) and len(data) >= 33 and data[12:16] == b"IHDR":
        mime = "image/png"
        width, height = struct.unpack(">II", data[16:24])
    elif data.startswith(b"\xff\xd8") and (size := _jpeg_size(data)) is not None:
        mime = "image/jpeg"
        width, height = size
    else:
        raise ReferenceFailure(
            422, "invalid_reference_image", "Only PNG or JPEG images are supported",
        )
    if not (
        MIN_REFERENCE_SIDE <= width <= MAX_REFERENCE_SIDE
        and MIN_REFERENCE_SIDE <= height <= MAX_REFERENCE_SIDE
    ):
        raise ReferenceFailure(
            422, "invalid_reference_image", "Reference image sides must be 64 to 2048 pixels",
        )
    return mime, width, height


class ReferenceImageStore:
    def __init__(self, database: Database, path: Path | None = None):
        # Do not create directories here: constructing OpenAPI must have no side effects.
        self.database = database
        self.path = path if path is not None else database.path.parent / "reference-images"

    @staticmethod
    def _item(row) -> ReferenceImage:
        return ReferenceImage(**{key: row[key] for key in ReferenceImage.model_fields})

    def _owner_directory(self, user_id: str, *, create: bool) -> int:
        if not _uuid(user_id):
            raise OSError("Unsafe owner directory name")
        if create:
            self.path.mkdir(mode=0o700, exist_ok=True)
        root = os.open(self.path, DIRECTORY_FLAGS)
        try:
            if create:
                try:
                    os.mkdir(user_id, 0o700, dir_fd=root)
                except FileExistsError:
                    pass
            return os.open(user_id, DIRECTORY_FLAGS, dir_fd=root)
        finally:
            os.close(root)

    def add(
        self, user_id: str, data: bytes, *, source: Literal["upload", "result"],
    ) -> ReferenceImage:
        mime, width, height = inspect_image(data)
        image_id = str(uuid4())
        digest = hashlib.sha256(data).hexdigest()
        directory = self._owner_directory(user_id, create=True)
        try:
            descriptor = os.open(
                image_id, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                dir_fd=directory,
            )
            try:
                view = memoryview(data)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("Reference write failed")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            try:
                with self.database.connect(write=True) as connection:
                    count, total = connection.execute(
                        "SELECT COUNT(*), COALESCE(SUM(byte_size), 0) FROM reference_images "
                        "WHERE user_id = ?", (user_id,),
                    ).fetchone()
                    if (
                        count >= MAX_REFERENCES_PER_OWNER
                        or total + len(data) > MAX_REFERENCE_BYTES_PER_OWNER
                    ):
                        raise ReferenceFailure(
                            409, "reference_quota_exceeded",
                            "Reference image limit reached; delete unused images first",
                        )
                    connection.execute(
                        "INSERT INTO reference_images (user_id, id, sha256, mime_type, width, "
                        "height, byte_size, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (user_id, image_id, digest, mime, width, height, len(data), source,
                         int(time.time())),
                    )
                    row = connection.execute(
                        "SELECT * FROM reference_images WHERE user_id = ? AND id = ?",
                        (user_id, image_id),
                    ).fetchone()
            except BaseException:
                os.unlink(image_id, dir_fd=directory)
                raise
        finally:
            os.close(directory)
        return self._item(row)

    def list(self, user_id: str) -> list[ReferenceImage]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reference_images WHERE user_id = ? ORDER BY created_at DESC, id",
                (user_id,),
            ).fetchall()
        return [self._item(row) for row in rows]

    def get(self, user_id: str, image_id: str) -> ReferenceImage | None:
        if not _uuid(image_id):
            return None
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM reference_images WHERE user_id = ? AND id = ?", (user_id, image_id),
            ).fetchone()
        return self._item(row) if row else None

    def read(self, user_id: str, image_id: str) -> tuple[ReferenceImage, bytes] | None:
        """Return metadata and bytes only when the stored file still matches its digest."""
        item = self.get(user_id, image_id)
        if item is None:
            return None
        try:
            directory = self._owner_directory(user_id, create=False)
        except OSError:
            return None
        try:
            descriptor = os.open(image_id, FILE_FLAGS, dir_fd=directory)
            try:
                details = os.fstat(descriptor)
                if not stat.S_ISREG(details.st_mode) or details.st_size != item.byte_size:
                    return None
                chunks = bytearray()
                while len(chunks) <= item.byte_size:
                    chunk = os.read(descriptor, 65536)
                    if not chunk:
                        break
                    chunks.extend(chunk)
            finally:
                os.close(descriptor)
        except OSError:
            return None
        finally:
            os.close(directory)
        data = bytes(chunks)
        if hashlib.sha256(data).hexdigest() != item.sha256:
            return None
        return item, data

    def in_use(self, connection, user_id: str, image_id: str) -> bool:
        rows = connection.execute(
            "SELECT definition_json FROM style_experiment_runs WHERE user_id = ? "
            "AND status IN ('running', 'stopping')", (user_id,),
        ).fetchall()
        for row in rows:
            character = json.loads(row["definition_json"]).get("character") or {}
            references = character.get("references", [])
            if any(reference.get("id") == image_id for reference in references):
                return True
        return False

    def delete(self, user_id: str, image_id: str) -> bool:
        if not _uuid(image_id):
            return False
        with self.database.connect(write=True) as connection:
            if connection.execute(
                "SELECT 1 FROM reference_images WHERE user_id = ? AND id = ?", (user_id, image_id),
            ).fetchone() is None:
                return False
            if self.in_use(connection, user_id, image_id):
                raise ReferenceFailure(
                    409, "reference_in_use", "Reference image is used by an active run",
                )
            connection.execute(
                "DELETE FROM reference_images WHERE user_id = ? AND id = ?", (user_id, image_id),
            )
        try:
            directory = self._owner_directory(user_id, create=False)
        except OSError:
            return True
        try:
            os.unlink(image_id, dir_fd=directory)
        except FileNotFoundError:
            pass
        finally:
            os.close(directory)
        return True


def _uuid(value: str) -> bool:
    try:
        return str(UUID(value)) == value
    except (ValueError, TypeError, AttributeError):
        return False
