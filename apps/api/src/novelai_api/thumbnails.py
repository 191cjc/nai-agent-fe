"""Small WebP previews of retained results for grid review; memory-only, bounded."""

import io
import threading
from collections import OrderedDict

from PIL import Image

THUMBNAIL_EDGE = 384
THUMBNAIL_QUALITY = 80
THUMBNAIL_CACHE_BYTES = 32 * 1024 * 1024
# Generation requests are at most 2048 px per side; refuse anything larger before decoding.
MAX_SOURCE_PIXELS = 2048 * 2048
# Decoding a 2048 px PNG takes ~16 MiB; two at a time keeps the small host responsive.
MAX_CONCURRENT_RENDERS = 2
RENDER_WAIT_SECONDS = 20


class ThumbnailBusy(Exception):
    """Every render slot stayed busy; the client may simply request again later."""


def render_thumbnail(png: bytes) -> bytes:
    """Downscale to THUMBNAIL_EDGE on the long side. The output carries no source metadata."""
    with Image.open(io.BytesIO(png)) as source:
        if source.format != "PNG" or source.width * source.height > MAX_SOURCE_PIXELS:
            raise ValueError("Unsupported thumbnail source")
        alpha = source.mode in ("RGBA", "LA", "PA") or "transparency" in source.info
        mode = "RGBA" if alpha else "RGB"
        pixels = source.convert(mode)
    pixels.thumbnail((THUMBNAIL_EDGE, THUMBNAIL_EDGE), Image.Resampling.LANCZOS)
    # A fresh image drops every info/text/ICC/EXIF entry the source PNG carried.
    clean = Image.new(mode, pixels.size)
    clean.paste(pixels)
    output = io.BytesIO()
    clean.save(output, format="WEBP", quality=THUMBNAIL_QUALITY, method=4)
    return output.getvalue()


class ThumbnailCache:
    """LRU of rendered previews keyed by (job, image). Results never change in place, so a
    key stays valid until the job expires or is deleted; callers re-check availability."""

    def __init__(self, *, max_bytes: int = THUMBNAIL_CACHE_BYTES,
                 concurrency: int = MAX_CONCURRENT_RENDERS, wait: float = RENDER_WAIT_SECONDS):
        self._max_bytes = max_bytes
        self._wait = wait
        self._entries: OrderedDict[tuple[str, int], tuple[str, bytes]] = OrderedDict()
        self._size = 0
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(concurrency)

    def get(self, job_id: str, user_id: str, index: int) -> bytes | None:
        with self._lock:
            entry = self._entries.get((job_id, index))
            if entry is None or entry[0] != user_id:
                return None
            self._entries.move_to_end((job_id, index))
            return entry[1]

    def render(self, job_id: str, user_id: str, index: int, png: bytes) -> bytes:
        if not self._slots.acquire(timeout=self._wait):
            raise ThumbnailBusy
        try:
            cached = self.get(job_id, user_id, index)
            if cached is not None:
                return cached
            data = render_thumbnail(png)
        finally:
            self._slots.release()
        with self._lock:
            key = (job_id, index)
            previous = self._entries.pop(key, None)
            if previous is not None:
                self._size -= len(previous[1])
            if len(data) <= self._max_bytes:
                self._entries[key] = (user_id, data)
                self._size += len(data)
            while self._size > self._max_bytes:
                _key, (_owner, evicted) = self._entries.popitem(last=False)
                self._size -= len(evicted)
        return data

    def discard(self, job_id: str) -> None:
        with self._lock:
            for key in [key for key in self._entries if key[0] == job_id]:
                self._size -= len(self._entries.pop(key)[1])

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._size = 0
