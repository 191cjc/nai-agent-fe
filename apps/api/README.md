# NovelAI workspace API

This backend provides SQLite migrations, administrator token management,
browser-cookie authentication, generation job/history APIs, private retained image
downloads, an authenticated DanbooruSearch tag-search adapter and a real
NovelAI Streamable HTTP MCP adapter and an isolated Codex advice runner. The web
app uses Vite HTTPS locally and host Nginx/systemd in production. The host
deployment procedure is in `../../deploy/README.md`; the remaining production
checks are tracked in
`../../.trellis/tasks/09-23-novelai-compose/implement.md`. With no MCP token configured,
generation returns `503 provider_unavailable`. With a valid MCP URL and token,
an authenticated generation request can make a **paid** upstream call. Tests
use mock transports and fakes; they never call paid services. Advice likewise
returns `503 advice_unavailable` without `NAI_CODEX_API_KEY`; with a key, an
explicit authenticated advice request can call the **paid** Codex service.

## Local setup

From `apps/api`, use Python 3.12+, `uv` and Node/npm:

```sh
uv sync --extra test
npm ci
export NAI_SQLITE_PATH="$(pwd)/var/data/novelai.sqlite3"
export NAI_PUBLIC_ORIGIN="https://localhost:5173"
uv run novelai-admin migrate
uv run novelai-admin create --label alice
uv run novelai-admin list
uv run novelai-admin revoke TOKEN_ID
uv run novelai-admin backup ./var/data/backup.sqlite3
uv run uvicorn novelai_api.app:app --host 127.0.0.1 --port 8000
uv run python -m pytest -q
uv sync --extra lint
uv run --extra lint ruff check src tests
```

`NAI_SQLITE_PATH` is a local file **path**, not a database URL. `migrate`
creates/upgrades the database explicitly; starting the API never creates one.
On POSIX, migration creates new data directories with mode `0700` and the
database file with mode `0600`; it restricts existing DB/WAL/SHM file modes
without altering pre-existing directory permissions. The operator must keep
the containing directory trusted and private, especially when using an existing
directory; restrictive file modes cannot undo any earlier disclosure. Backup
outputs are created exclusively with mode `0600`. Windows deployment needs
separate ACL validation.
The database location and `.env.local` are private and must not be committed.
The older `.env.local` may have obsolete database/media/hash-key settings: do
not treat it as a runnable configuration or overwrite any filled secrets.
New tokens are generated server-side and printed **once**; only SHA-256 hashes
are stored. The operator must securely distribute issued tokens to users.

To explicitly reset every user's saved random training-set recipes, run this
operator-only command against the intended `NAI_SQLITE_PATH`:

```sh
uv run novelai-admin clear-dataset-recipes --all-users
```

The required `--all-users` flag makes the scope explicit. The command deletes
only `dataset_recipes` in one transaction and prints `{"deleted_recipes": N}`;
it never loads or prints recipe names or JSON. Generated training sets, frozen
run items, generation history, captions, images and authentication records stay
intact. This reset is never run by startup, migration or an HTTP route. After
refreshing the editor, users with no saved recipes start from the current
built-in template and can save their own copy.

The `__Host-nai_session` cookie requires HTTPS, and mutations require an
`Origin` exactly matching `NAI_PUBLIC_ORIGIN`. Local browsers use Vite's
HTTPS proxy; production browsers use the existing HTTPS Nginx origin.
Direct loopback HTTP is for health and operator checks, not browser login.

Set `NAI_NOVELAI_MCP_URL=https://www.fsstudy.com.cn/novel-ai-v5` and provide
`NAI_NOVELAI_MCP_TOKEN` in the server environment to enable generation.
The deployed MCP endpoint is the **base path**, not the `/mcp` path: a
non-billable `initialize` / `tools/list` probe succeeded at the base path,
while the old `/mcp` URL returned HTML. The operator has corrected the private
`.env.local` URL; the app reads process environment variables, **not that file
automatically**. At generation time, the adapter checks the tool schema before
making at most one `tools/call`; it does not retry uncertain paid outcomes.
Each RPC response has a 48 MiB decoded cap and bounded gzip/deflate decoding.
Its monotonic deadline starts before opening the response and is checked between
raw chunks, after EOF and after parsing. A blocked synchronous read still relies
on HTTPX's connect/read timeouts; this is not a hard wall-clock interruption.
The probed schema declares `model` and `sampler` as strings, not enumerated
choices. Confirm actual supported values and image metadata before presenting
production UI options; no paid generation has been run to verify them.

Tag search uses the configured public REST provider only when an authenticated
user submits a request. It explicitly includes NSFW candidates, returns
normalized tags without modifying prompts and includes a provider attribution
URL. The adapter permits one in-flight search, bounds decoded upstream
responses to 1 MiB (including gzip/deflate), and checks a 30-second monotonic
deadline between network operations and after parsing. Individual blocked reads
remain governed by HTTPX's read timeout. Tests use an injected
`httpx.MockTransport` and never call the real
service. A manual, non-billable adapter probe on 2026-10-08 searched for
`蓝色长发` and returned normalized `long_hair` and `blue_hair` candidates with
Chinese names, NSFW flags and scores. This one-query check is separate from
the automated suite and does not establish continuous provider availability.
When the provider returns 429, the API forwards a valid `Retry-After` value
(nonnegative seconds or HTTP date) in its own 429 response. Invalid or unsafe
values are omitted; the API never retries the search automatically. A locally
busy search also returns 429, but without an upstream `Retry-After` header.

## Generation contract (tested with mocks and fakes)

An authenticated `POST /api/generations` accepts a positive and negative
prompt, model, width/height (multiples of 64), steps, CFG scale, sampler,
optional seed, sample count and boolean quality toggle. `seed: null` chooses
an explicit random seed before the provider call. `GET /api/generations/{id}`
shows status and retained owner-only image URLs; `GET /api/generations`
lists paginated **parameter-only** history with 1-100 records per request
(20 by default) and no 10,000-record cutoff; offsets use the JavaScript-safe
integer range. `DELETE /api/generations/{id}`
deletes a finished record and its image files. Active jobs cannot be deleted.
Images use private disk storage in generation-images/ beside SQLite and remain
until explicitly deleted, including images with former seven-day manifests.
`result_expires_at` is null for retained disk images. Prompts, parameters and
experiment metadata persist in SQLite until deleted. See the image-retention
contract under .trellis/spec/backend/ for bounded capacity and pre-paid storage admission.
For consistent backups of a live SQLite database, run the admin `backup`
command to a new private path, never copy only the active database file while
WAL is in use. Backup retention and restore drills belong to the deployment
task; backups contain prompts and token hashes but no image bytes.

The optional `style_prompt` and `character_prompts: [{"prompt": "..."}]`
fields preserve style and native independent characters in parameter history.
`positive_prompt` is shared scene content. Only style and shared content are
combined into the provider's base prompt; character descriptions remain
separate. Legacy records default to empty style and no characters. The base
must be nonblank and at most 3000 characters; each character is nonblank and
at most 3000 characters, with a workspace limit of six characters.

Character-bearing requests require a supported ordinary V4/V4.5/V5 model ID
and the provider's object-array `character_prompts` capability. Unsupported
requests fail before a paid call rather than combining or dropping characters.
Characters accept normalized x/y coordinates in 0.1–0.9, defaulting to
0.5. The editor provides drag/keyboard positioning; automatic placement remains
deferred. Exact fields,
model IDs and compatibility rules are in
`../../.trellis/spec/backend/native-character-contract.md`. The deployed
schema confirms the argument exists; real image output has not been verified.
Flat requests retain free-form model/sampler IDs. Deploy the new API before
the new frontend so an old API cannot ignore the additive structured fields.

## Codex advice runtime

The API uses `openai-codex-sdk==0.1.11` with the project-local
`@openai/codex==0.152.1` native CLI. Run `npm ci` in `apps/api` locally, or
`npm ci --omit=dev` in a host release, before enabling advice. Keep
`node_modules` beside `src`: the runner resolves the pinned native binary
from that layout. Set `NAI_CODEX_API_KEY` in the API environment to enable it;
leave it unset to return `503 advice_unavailable`. The runtime uses the
official default Codex provider endpoint. It does not need a custom URL or
model setting, and it does not use an inherited CLI login or read `.env.local`
automatically. Never place the key in browser configuration or source control.

Each request creates a private temporary work directory and `CODEX_HOME`. The
pinned CLI receives the configured key via `codex login --with-api-key` on stdin
inside that temporary home; the SDK child receives no API key in its environment.
The runner starts a new thread for only the submitted advice text, uses a
read-only sandbox, network/search disabled and approval policy `never`, and
requests named tool-capability switches off in its fresh config. The pinned CLI
still reports `unified_exec` enabled when explicitly set to `false`; its
`shell_tool` switch reports disabled. It requires strict JSON matching
`{ "suggestion": "..." }`, rejects observed tool-item events, stops the SDK
child before cleanup, and deletes the temporary home after success, timeout,
cancellation or shutdown.
The existing advice service admits at most two concurrent turns and imposes a
45-second deadline. Advice input and output are not saved in SQLite.

These sandbox settings and event checks do not prove that every tool is
unavailable before execution. Event rejection happens after an event is
observed and cannot rule out a side effect before that event.
Keep the API host and process credentials private, and do not treat this runner
as a pre-execution no-tools security boundary.

## Browser API contract

`contracts/openapi.json` is the checked-in, credential-free schema for the
web application. `tests/test_api_contract.py` compares it with the
current FastAPI OpenAPI output using fake settings, so route or response
changes require an intentional contract review. API requests use same-origin
`/api/*` internally; `NAI_PUBLIC_ORIGIN` is only the HTTPS scheme, host and
optional port, never the UI path. Production browsers use `/novelai/api/*`
on the selected `/novelai/` UI route. The proxy strips `/novelai` before
forwarding to the unchanged backend `/api/*` routes, while the web client
prefixes returned authenticated image paths for browser fetches.

Generation and experiment-group details include `parameters` (complete workspace
input, including private comments/sections) and nullable `provider_request`
(the actual allowlisted arguments captured before the MCP `generate_image`
call). History lists omit the latter. Old records have no capture; uncertain
outcomes retain the attempted arguments without automatic retries. These are
the configured MCP service's inputs, not its internal downstream HTTP body.
Modern editor requests replace physical prompt line endings with spaces only
at the provider boundary, after removing hidden comments. Raw workspace inputs
and previously captured requests retain their original text.
This requires schema5 (`0005_provider_requests.sql`): run the explicit
`novelai-admin migrate` before API readiness and publish the API before the web.
Preserve private backups and existing data; retain the compatible API on web fallback.

The schema describes the advice response type; actual availability depends on
the explicit Codex key and installed pinned CLI. Model and sampler identifiers
remain provisional until the operator verifies accepted values;
do not ship fixed choice lists inferred from this snapshot.


Saved style experiments attach optional experiment metadata to each ordinary
generation request; this is never forwarded to NovelAI. GET
/api/style-experiments lists owner-scoped saved groups, and GET
/api/style-experiments/{id} pages GenerationView rows in exact ordinal order.
Viewing history never restarts a paid batch. Metadata remains after image
expiry; SQLite backups do not include separately stored PNG bytes.

Durable style batches use schema3 (0003_style_experiments.sql) and
/api/style-experiment-runs creation, /active observation, /{id} polling and
/{id}/stop. They persist compact definitions, effective seed, cursor and counts,
share the existing bounded generation executor, continue to the next distinct
group after failures and survive browser/API restart without repeating an
interrupted group. One active run per owner; logout detaches observation only.
Run the explicit migration before readiness and keep this API after any web
fallback. Restore drills must disable copied active runs and all providers.
