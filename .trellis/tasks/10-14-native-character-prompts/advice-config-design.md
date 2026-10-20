# Advice Configuration Reuse (2026-10-20)

## Problem and authority

Production advice/translation returns503 advice_unavailable because neither
/etc/novelai/api.env nor the running API has NAI_CODEX_API_KEY. The user
explicitly authorized reusing AiQQ AI configuration and requested the later
key-edit location. AiQQ's selected text backend uses a key, a custom HTTPS
Responses base and an explicit model; copying only the key would target the
wrong endpoint. Parent securely confirmed available settings without exposing
credentials. Copy once into the NovelAI root0600 config, not live-sync AiQQ.

## Smallest change

Backend Settings gains optional NAI_CODEX_BASE_URL and NAI_CODEX_MODEL. Unset
values preserve the existing SDK/CLI default behavior. Validate an explicitly
configured endpoint as an absolute HTTPS URL with hostname and no userinfo,
query, fragment or whitespace/control characters. Validate configured model as
a nonblank bounded identifier (<=200, no whitespace/control characters).
Wire optional values through create_app to CodexAdviceRunner. Use pinned
SDK0.1.11 options.base_url and thread.model, only when configured. Retain stdin
API-key login; do not pass api_key to SDK options or inherit host environment.
No custom provider auth, SDK upgrade, model migration, tools, auto-retry or
browser/API/schema/database/generation behavior changes. Existing restrictions,
timeout, bounds, cleanup and secret-free failure handling stay intact.

Expected product files: apps/api/src/novelai_api/{config,codex_advice,app}.py,
existing test_advice.py plus test_auth.py or focused config tests if needed,
deploy/.env.api.example and deploy/README.md for private key/address/model
rotation instructions. Main owns specs/task artifacts/production/helpers.
No frontend changes or automated frontend/helper/browser tests.

## Verification and release

Use fakes to prove settings/defaults/rejection, configured app wiring and exact
SDK base/model propagation without keys in child env/options, source leakage
or weakened tool restrictions. Existing default isolation tests remain. Run
full fake backend suite, frozen sync/lock, Ruff src/tests and unchanged exact
OpenAPI; no real AI/provider calls, token issuance or credential output.
Independent native check follows implementation, including release helper
source review. API-only publication preserves the existing web release/assets,
AiQQ service/config, schema4, NovelAI provider settings/auth/rows/private images
and original expiry. Stage immutable source/locks/pinned CLI and disposable
schema/readiness. Before restart verify idle, online private backup, stop
cleanly/recheck idle and capture image inventory. Back up original root0600
env, privately atomically copy only the authorized three AI settings, then
switch/start API and verify exact OpenAPI/readiness and expected config.
After modern startup attempt leave process/pointer intact on later failure;
forward-fix rather than repeated recovery restarts. No live DB restore.

Final key location: /etc/novelai/api.env NAI_CODEX_API_KEY, with optional
NAI_CODEX_BASE_URL / NAI_CODEX_MODEL. Future edits use sudoedit and an idle
novelai-api restart. AiQQ's original file remains independently maintained.
Real translation quality remains user acceptance; task stays in_progress.
