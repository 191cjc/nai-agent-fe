# Verification: Sampler Choices

Date: 2026-10-15. Independent follow-up source review; no defects found and
no source fixes required. The only source diff is `apps/web/src/App.tsx`.

## Reviewed behavior

- All seven displayed names and exact IDs match the pinned enum recorded in
  `research/sampler-options.md`. The actual select has a disabled empty
  placeholder, readable preset names plus IDs, and explicit manual entry.
- A new draft keeps `sampler: ''`; rendering and opening settings do not
  choose a default. Selecting a preset writes its exact ID and exits manual
  mode. Selecting manual entry preserves the existing draft string.
- Manual typing latches component-local manual mode before updating the
  draft, so typing a known preset ID does not hide/recreate the input. Unknown
  history values open the manual input without coercion. History reuse while
  manual mode is active replaces the displayed draft value while keeping it
  editable; reuse otherwise derives the appropriate preset/manual view.
- The UI-only `manual` option never writes its sentinel to the draft. A custom
  or historical sampler whose literal value is `manual` remains editable and
  is preserved as ordinary draft text. Each label contains one control.
- `Workspace` keeps `SettingsPanel` mounted while hidden, preserving local
  mode and draft values. Select/input changes only edit settings; they have no
  render/effect writes, submission handlers or provider calls.
- `GenerationStore.setField`, `reuse` and `requestFromDraft` retain the sole
  sampler string; ordinary submission uses the existing validation/trim path.
  Style experiments copy the validated string into their frozen snapshot and
  later combinations use that snapshot, unaffected by settings/history edits.
- No store/default/model/API/schema/dependency, generation lifecycle or
  compatibility-matrix changes were introduced. Existing select styles apply.

## Checks and limits

- ESLint: passed via `npm run lint` in `apps/web`.
- TypeScript: passed via the same script's `tsc --noEmit`.
- Lint child process environment was cleared, retaining only normal PATH/HOME
  plus offline npm mode and separate empty user/global npm config files.
- `git diff --check`: passed.
- No frontend/helper automated tests, browser automation, paid calls,
  production/API access or configuration/credential reads were performed.
  Build, publication and interactive/provider acceptance remain with the main
  session/operator; static review does not establish runtime provider output.

Source ownership handed back to the main session; no further App.tsx writes
are pending from this reviewer.

## Main session: clean build

Production build passed in `/tmp/nai-sampler-options-web-bqdd41tk`, using only
package.json, package-lock.json, index.html, tsconfig.json, vite.config.ts and
src. No `.env*` entered the stage. The process environment was cleared except
normal PATH/HOME and explicit npm/build settings; npm user/global configs were
distinct empty files. Locked archives had HTTPS URLs and integrity hashes;
`npm ci --offline` preceded the `/novelai/` production build.

All 14 staged input hashes matched the final source, including the reviewer's
App.tsx hash. Input-map SHA-256:
`c8395ec6e5555f5feb03ce978edc4675ed9f144ab57fa969ff0574ef76eebb85`.
Publication also compares this map against the work commit before installing
dist. Public HTTP/resource checks and operator interaction remain separate.
