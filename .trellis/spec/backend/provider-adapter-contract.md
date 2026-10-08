# Tag Provider Adapter Contract

## Scope / Trigger

When changing `apps/api/src/novelai_api/tags.py`, compare the provider's
`TagOut` response with the workspace's typed `TagCandidate`. Do not infer
wire fields from names chosen for the public API.

## Signatures

- `POST /api/tags/search`: authenticated `SearchRequest(query: str, limit: int)`
  passed to `TagSearch.search(request) -> SearchResults`.
- `_candidate(raw: object) -> TagCandidate | None` isolates provider data
  from the browser-visible schema.
- `_safe_retry_after(value: str | None) -> str | None` validates the
  upstream 429 header before `POST /api/tags/search` exposes it.

## Contracts

- Send `POST {NAI_DANBOORU_SEARCH_API_URL}/search` with `query`, `limit`, and
  `show_nsfw: true`. Never auto-insert a tag into the generation prompt.
- Upstream `TagOut` has `tag`, `cn_name`, `nsfw` (string), `final_score`
  (number), `count`, `category`, and `wiki`. Accept legacy fake payloads
  with `is_nsfw` (boolean) and `score` (number) as fallbacks.
- Return only typed `TagCandidate` fields and source attribution, never raw
  upstream errors or API keys.
- Stream upstream response bodies with a 1 MiB **decoded** limit and a
  30-second monotonic total deadline (five-second connect timeout). Accept
  bounded identity, gzip and deflate results; never buffer an unlimited body.
  Inspect error statuses before consuming their bodies.
- On upstream 429, retain the typed `ApiError(code="search_rate_limited",
  retryable=true)` and forward only a valid `Retry-After` response header.
  Accept ASCII nonnegative delta-seconds or a valid HTTP date; normalize
  numeric seconds and dates, trim surrounding HTTP whitespace, and drop values
  over 128 characters or containing CR/LF or invalid control characters. Do not
  read the 429 response body or retry automatically.
  The local `search_busy` 429 does not inherit an upstream header.

## Validation & Error Matrix

| Upstream value | Normalized value |
| --- | --- |
| `nsfw: "1"` / `"0"` | `is_nsfw: true` / `false` |
| Unknown or missing `nsfw` | Valid legacy boolean, otherwise `null` |
| Finite numeric `final_score` | `score: float` |
| Invalid/non-finite `final_score` | Legacy finite `score`, otherwise `null` |
| Invalid canonical `tag` | Drop candidate; keep valid siblings |
| Oversized or corrupt 200 response | `502 search_bad_response` |
| Total deadline or read timeout | `504 search_timeout`, retryable |
| Upstream 429 with valid `Retry-After` | `429 search_rate_limited`, validated header included |
| Upstream 429 with invalid/missing `Retry-After` | `429 search_rate_limited`, header omitted |
| Local capacity 429 (`search_busy`) | `429 search_busy`, header omitted |

Keep normalized 429, 422, timeout and transport-error mappings.

## Good / Base / Bad Cases

- Good: `{"tag":"safe","nsfw":"0","final_score":0.85}` yields
  `is_nsfw: false`, `score: 0.85`.
- Base: `{"tag":"unknown"}` stays visible with nullable metadata.
- Bad: `{"tag":"bad","nsfw":"maybe","final_score":"0.85"}` never
  becomes NSFW-true or a guessed score.
- Good: upstream 429 with `Retry-After: 00042` returns `Retry-After: 42`
  without changing the JSON error body.
- Base: upstream 429 without a retry value returns the typed error only.
- Bad: a multiline or negative retry value is never copied to a browser
  header, even when the upstream status is 429.

## Tests Required

- Use `httpx.MockTransport` and disposable SQLite in
  `apps/api/tests/test_tags.py`; automated tests do not contact live or
  paid providers.
- Assert real upstream keys, `show_nsfw: true`, known and unknown safety
  values, non-finite scores, fallback and precedence, and secret-free errors.
- Assert that compressed expansion cannot exceed the decoded cap, malformed
  gzip fails safely, slow chunks exceed the overall deadline, and an upstream
  429 body is not read. Verify the single-request capacity releases on errors.
- Check numeric/date normalization, invalid/oversized/CRLF suppression,
  upstream-only propagation, unchanged typed error/status and the documented
  OpenAPI 429 header via `apps/api/tests/test_api_contract.py`.

## Wrong vs Correct

- Wrong: read only `raw["is_nsfw"]` and `raw["score"]`; actual `TagOut`
  fields then disappear.
- Correct: normalize `raw["nsfw"]` and `raw["final_score"]` first, accept
  legacy keys as fallback, and keep the browser-visible schema stable.
- Wrong: `client.post()` reads an arbitrary upstream body in full, or treats
  an HTTPX per-read timeout as a whole-request deadline.
- Correct: bound the decoded streamed response and check a monotonic deadline
  between chunks before parsing the bounded JSON document.
- Wrong: echo an upstream `Retry-After` header without validation or
  automatically repeat a request after receiving 429.
- Correct: validate and forward the header only on upstream 429; leave any
  retry decision to the caller.
