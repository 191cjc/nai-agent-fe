# Bounded HTTP Response Contract

## Scope / Trigger

Use this contract for `apps/api/src/novelai_api/_http_response.py` and the
NovelAI MCP and tag-search adapters that consume it. It owns response-body
reading and decompression; each adapter owns HTTP statuses, JSON/protocol
validation, credentials and public error mapping.

## Signatures

- `read_bounded_body(response: httpx.Response, *, max_bytes: int,
  deadline: float, clock: Callable[[], float]) -> bytes`
- `check_deadline(deadline: float, clock: Callable[[], float]) -> None`
- Internal failures are `ResponseDeadlineExceeded` and `InvalidResponseBody`.
  Neither is an API error or a reason to retry a paid call.

## Contracts

- Pass an absolute monotonic deadline established **before** opening the
  response, and a positive adapter-specific decoded-byte cap. MCP uses
  `MAX_RESPONSE_BYTES` (48 MiB) per RPC; tag search uses 1 MiB per search.
- Read transport chunks with `iter_raw()` without fixed-size aggregation.
  Check deadlines between received chunks, through decoding and after EOF;
  adapters also check after JSON/SSE parsing. A synchronous blocked network
  read is still governed by HTTPX's connect/read timeouts. This is a cooperative
  deadline, not a hard wall-clock interruption guarantee.
- Accept identity, gzip and wrapped/raw deflate. Split raw input into bounded
  pieces and call `zlib.decompressobj().decompress(data, max_length)` with only
  the remaining decoded allowance plus one overflow-detection byte. Enforce
  the cap before retaining output; do not let HTTPX expand arbitrary compressed
  input before checking its size.
- Reject unsupported encodings, invalid/truncated compressed streams and
  trailing compressed data. Require decoder EOF. Do not rely on
  `decompressobj.flush(length)` for an output cap: its argument sets the initial
  buffer size rather than a maximum allocation.
- Already consumed responses from fake transports contain decoded bytes;
  check their length directly. Real `client.stream()` responses use the raw
  path. A buffered fake cannot prove production decompression bounds.
- Preserve each adapter's error codes, HTTP status handling and no-retry
  behavior. The MCP adapter sends at most one `tools/call` per generation.

## Validation & Error Matrix

| Condition | MCP before paid call | MCP paid response | Tag search |
| --- | --- | --- | --- |
| Cooperative deadline exceeded | `invalid_mcp_response` | `outcome_unknown` | `504 search_timeout` |
| Decoded cap exceeded or invalid compression | `invalid_mcp_response` | `outcome_unknown` | `502 search_bad_response` |
| HTTPX read timeout | `provider_unavailable` | `outcome_unknown` | `504 search_timeout` |
| HTTPX request failure | `provider_unavailable` | `outcome_unknown` | `503 search_unavailable` |

Provider-specific HTTP status and JSON/protocol validation mappings remain
in their adapters; this table describes body-reading failures only.

## Good / Base / Bad Cases

- Good: a gzip response with a small decoded cap aborts after at most the
  remaining allowance plus one decoded byte, without reading later chunks.
- Base: valid identity/compressed JSON and MCP SSE parse through the same
  bounded reader, including a deflate header split across tiny chunks.
- Bad: `iter_bytes(chunk_size=65536)` waits for 64 KiB before checking time,
  allowing a slow stream to hold the only generation worker past its deadline.

## Tests Required

- Use `httpx.MockTransport`, fake raw byte streams and an injected/patched
  monotonic clock. Never use sleeps or a live provider to prove deadline behavior.
- Regress slow tiny chunks, deadlines before response opening/after EOF,
  valid compressed JSON/SSE, split raw-deflate headers, decoded expansion,
  malformed/truncated compression and uncertain paid results without retries.
- Run existing tag tests after shared-reader changes to preserve NSFW
  normalization, rate-limit headers, decoded caps and timeout behavior.
- Inspect decompressor `max_length`/decoded output in expansion tests; a
  post-expansion error alone does not prove bounded allocation.

## Wrong vs Correct

- Wrong: call HTTPX's automatic decoded iterator and reject a huge chunk only
  after it has already been decompressed, or claim a fixed-size iterator gives
  a total request deadline.
- Correct: bound raw-chunk decompression itself, check the monotonic deadline
  between transport operations and preserve HTTPX per-read timeout limits.
