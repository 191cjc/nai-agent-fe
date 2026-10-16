# Automatic or Manual Character Position

## Authorization and Boundary

The operator reports an updated deployed MCP: character_prompts without x/y
use automatic placement; coordinates preserve manual placement; optional
auto_character_position explicitly selects the mode. Ignore the supplied
external documentation path. Fresh non-billable discovery against the
application's configured provider confirms nullable boolean support in
research/deployed-mcp-auto-position-schema.json. It does not prove image
appearance. The older source research is historical at this boundary.

The operator initially prohibited restart while work was active, then explicitly
authorized restart with "现在可以重启服务" on 2026-10-16. Finish independent
checks and a clean build before coordinated API-first publication. Preserve
configuration, private state and retained assets; inspect active work and verify
a private online backup before restarting. No paid probes, frontend/helper
automated tests, browser work, new credentials or messages.

Smallest gap: this workspace always sends x/y and has no positioning mode.
The mode belongs in typed request/draft/history/run snapshots and MCP mapping,
with one selector beside the existing character-position board. Preserve the
existing manual coordinate bounds/editor and all generation safeguards.

## Public and Stored Contract

- GenerationRequest adds strict auto_character_position: bool = False.
  No null/string/number coercion. Existing API callers/history/run definitions
  default to manual to preserve frozen behavior. No SQLite migration.
- CharacterPrompt's existing strict finite x/y defaults and bounds stay
  unchanged. Coordinates remain in the workspace request and saved metadata
  even in automatic mode, for lossless switch-back/reuse. The adapter alone
  omits them from automatic MCP children. This avoids confusing omitted old
  saved coordinates (historically centered) with a new user mode selection.
- Browser wire field is optional for legacy responses; draft state owns a
  required boolean defaulting false. Save/reuse/reset/latest-history restore,
  immutable style-run snapshots and summaries must preserve the mode.
- Canonical same-id run comparison must normalize only an absent saved
  parameters.auto_character_position to False. Preserve original definition
  bytes, plan_version1/2 selection and conflict on changed mode or other keys.
  Do not broadly erase unknown definition keys or rewrite old definitions.

## MCP Mapping and Capability

- With no nonblank characters, preserve the original eleven MCP arguments,
  irrespective of the mode flag.
- With characters, retain native model and character object-array checks.
  Automatic: require the newly advertised optional argument to accept true;
  emit auto_character_position=true and ordered child objects containing
  prompt, negative_prompt='', enabled=true, with x/y entirely absent.
- Manual: emit every validated x/y exactly. If the optional schema is known
  to accept false, explicitly emit false. Old/missing/incompatible flag support
  may retain coordinate-only manual payload compatibility. Never fall back
  from requested automatic placement to centered/manual placement.
- Recognize the verified boolean or nullable-anyOf boolean form conservatively
  (ignore annotations, reject unknown validation constraints). An unsupported
  automatic request fails before tools/call with a safe actionable
  unsupported_auto_character_position diagnostic, without paid retry.
- The adapter already creates a fresh MCP session and calls tools/list for
  every generate operation. Retain that lifecycle; no long-lived schema cache
  or service reconnect/restart is necessary for schema discovery.

## UI Behavior

- One global automatic/manual selector in CharacterPositions. Default manual
  preserves the existing draft behavior. Auto explains that NovelAI chooses
  composition; keep input values in the draft, hide/disable drag controls and
  cancel any active pointer capture/drag. Switching back restores positions.
- Use native accessible controls with labels and no implicit submission.
  Mode changes increment the existing draft revision so pending entry restore
  cannot override user edits. Preserve stable character IDs, coordinates,
  tag targets, focus, keyboard behavior and all prompt-drawer state.
- PromptSummary displays automatic placement instead of authoritative saved
  x/y for automatic records; manual and legacy records show coordinates.
  Mode selection must not change a running server experiment's frozen mode.
- Product copy describes the user's placement choice, not MCP serialization.

## Ownership and Validation

Native implementer owns apps/api generations.py, mcp_images.py,
style_experiments.py, affected fake-only regressions and reviewed OpenAPI;
web api.ts, store.ts, CharacterPositions.tsx, PromptSummary.tsx and necessary
scoped styles. Parent owns artifacts/specs/build/journal; preserve other edits.
No unrelated layout, provider, character-negative, per-character-mode or
schema/version/dependency refactor.

1. Implement directly with trellis-implement; no nested agents. Add meaningful
   offline regressions for strict/default mode validation, exact auto/manual/
   legacy/flat MCP arguments, capability failures before tools/call, history
   persistence/restore and frozen run seed/coordinates/mode across restart.
   Check legacy run idempotency and changed-mode conflict with unchanged raw
   definition. Intentionally review the additive OpenAPI snapshot.
2. Independent trellis-check runs full frozen offline backend pytest/Ruff/lock
   and frontend ESLint/TypeScript/source review; no frontend/helper/browser
   tests or paid calls. Verify pointer/keyboard/focus cleanup and entry epochs.
3. Parent updates executable specs, builds fresh explicit env-free locked web
   inputs, records a private build/release-readiness artifact and scoped commits
   (no push/amend). Stage committed matching API/web, verify private online
   backup and idle state, then activate API first and compare its running
   OpenAPI before publishing the web. Verify public hashes, health, retained
   assets and configuration continuity. Keep the new API on web fallback once
   automatic-mode records have been accepted; never restore the live DB.
4. Record release evidence and journal; the broader task remains in_progress
   for real-provider appearance and operator interaction acceptance.
