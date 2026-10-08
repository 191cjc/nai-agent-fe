"""Bounded response decoding shared by the backend HTTP provider adapters."""

import zlib
from collections.abc import Callable, Iterator

import httpx

_RAW_CHUNK_BYTES = 8192


class ResponseDeadlineExceeded(Exception):
    pass


class InvalidResponseBody(Exception):
    pass


def check_deadline(deadline: float, clock: Callable[[], float]) -> None:
    if clock() >= deadline:
        raise ResponseDeadlineExceeded


def _raw_chunks(
    response: httpx.Response, deadline: float, clock: Callable[[], float]
) -> Iterator[bytes]:
    # No fixed-size HTTPX aggregation: even a tiny transport chunk must give
    # the caller a chance to check its deadline. A blocked read still relies
    # on HTTPX's per-read timeout; this is not an interruptible wall clock.
    for raw_chunk in response.iter_raw():
        check_deadline(deadline, clock)
        for start in range(0, len(raw_chunk), _RAW_CHUNK_BYTES):
            check_deadline(deadline, clock)
            yield raw_chunk[start : start + _RAW_CHUNK_BYTES]


def read_bounded_body(
    response: httpx.Response,
    *,
    max_bytes: int,
    deadline: float,
    clock: Callable[[], float],
) -> bytes:
    check_deadline(deadline, clock)
    encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
    if encoding not in ("identity", "gzip", "deflate"):
        raise InvalidResponseBody
    if response.is_stream_consumed:
        # Mock transports may return already decoded, buffered responses.
        # Production client.stream() responses take the raw path below.
        body = response.content
        if len(body) > max_bytes:
            raise InvalidResponseBody
        check_deadline(deadline, clock)
        return body

    body = bytearray()
    size = 0
    decoder = zlib.decompressobj(zlib.MAX_WBITS | 16) if encoding == "gzip" else None
    deflate_prefix = b""
    for chunk in _raw_chunks(response, deadline, clock):
        if encoding == "deflate" and decoder is None:
            # Wait for the complete zlib header before choosing wrapped or
            # raw deflate, including when the transport sends single bytes.
            deflate_prefix += chunk
            if len(deflate_prefix) < 2:
                continue
            chunk = deflate_prefix
            wrapped = chunk[0] & 0x0F == 8 and chunk[0] >> 4 <= 7
            wrapped = wrapped and int.from_bytes(chunk[:2], "big") % 31 == 0
            decoder = zlib.decompressobj(zlib.MAX_WBITS if wrapped else -zlib.MAX_WBITS)
            deflate_prefix = b""
        if decoder is not None:
            try:
                # max_length bounds allocation itself, before the adapter
                # can inspect the expanded result. One extra byte detects
                # overflows even at the exact configured cap.
                chunk = decoder.decompress(chunk, max_bytes - size + 1)
            except zlib.error as exception:
                raise InvalidResponseBody from exception
            if decoder.unused_data:
                raise InvalidResponseBody
        size += len(chunk)
        if size > max_bytes:
            raise InvalidResponseBody
        body.extend(chunk)
        check_deadline(deadline, clock)

    check_deadline(deadline, clock)
    if encoding != "identity" and (
        decoder is None or not decoder.eof or decoder.unused_data
    ):
        raise InvalidResponseBody
    # With no output-limit overflow, decompress consumed all input and eof
    # proves the stream is complete. flush(length) is deliberately avoided:
    # its length only sets the initial buffer size, not an output ceiling.
    result = bytes(body)
    check_deadline(deadline, clock)
    return result
