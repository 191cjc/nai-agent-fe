# Per-section Assistant Independent Check

Date: 2026-10-16. Scope: the seven affected frontend sources and the web-only
build/publication helpers. Review began with design/spec/helper reads only;
frontend source inspection started after the parent declared SOURCE FROZEN.

## Findings (fixed)

- File: `/tmp/nai-section-assistant-publish.py` (parent-owned release helper).
  The original helper compared hashes only for inputs listed in the build
  manifest. A source file added after the build could therefore escape its
  committed/working/build equality gate. The parent added exact file-set
  equality across the clean-build manifest, working `src` plus five root build
  inputs, and committed Git `src` plus those inputs, before the existing
  individual SHA-256 checks. Working source symlinks are rejected. Read-only
  re-review confirms this finding is resolved; the executable deployment spec
  also records the file-set boundary. No helper tests or publication executed
  by this reviewer.

No frontend source corrections were needed.

## Findings (not fixed)

None. No unresolved in-scope behavior defect or design decision was identified.
Desktop/mobile interaction and actual AI/search content remain operator
acceptance; static source review does not establish those runtime outcomes.

## Affected-source review

- `SectionAssistant.tsx` provides one independent, body-portaled nonmodal
  dialog with AI/search tabs. Opening/tab changes do not request anything.
  Explicit advice sends only the visible editable consultation seeded from the
  opening label/text, and displays a bounded editable plain-text suggestion.
  Search applies canonical tags with explicit append/replace controls and
  shows translations, NSFW/source and optional metadata. No left tool store is
  read or changed, and no response automatically changes the generation draft.
- `App.tsx` owns one local assistant opening with an exact target, stable
  person ID and separate draft identity revision. Drawer/prompt-panel hiding,
  reuse/reset/logout/disposal and missing target invalidate the opening. A
  sibling's removal cannot redirect application; the displayed person number
  is resolved from its stable ID. Existing style-experiment controls remain.
- `PromptSections.tsx` reuses the trigger for all fixed shared/person sections,
  including hidden sections, while preserving hide/save/import and snapshot
  selection/mapping. Style and negative headings use the same helper.
- `GenerationStore.applyPromptText` resolves the exact current destination,
  checks opening identity, constructs an independent proposed section draft
  and validates before writing only destination text plus the draft revision.
  Append preserves raw nonblank text and duplicates; replace affects one text
  only. Enabled flags, coordinates, siblings, settings and global tag target
  remain intact. Relevant field/effective composition limits apply without
  requiring model/sampler/seed/nonblank-base completion or validating an
  unrelated prompt group. Default full section validation remains in ordinary
  generation and snapshot import. Negative application has its own 3000 limit.
- `WorkspaceApi.search/advice` add only optional AbortSignal arguments. Wire
  requests, existing auth/session handling and the left tool callers remain
  unchanged. Each local request has abort/controller/epoch/alive/current-target
  guards; edits cancel superseded requests. Close/replacement/unmount clean
  request ownership and cooldown intervals; there is no automatic retry.
- The portal escapes prompt-drawer overflow. Positioning clamps to the visual
  viewport and updates on scroll/resize/mobile-keyboard changes and bounded
  resize/mutation observations. Own scrolling bounds long advice/results.
  Hidden/disconnected/clipped openers close it. Buttons are `type=button`;
  explicit search Enter and advice Ctrl/Command+Enter cannot submit generation.
  Arrow/Home/End handling stays in its tablist. Captured Escape closes only the
  assistant; outside pointer/focus closes it. Cleanup returns focus only when
  appropriate to a connected visible opener or safe prompt disclosure fallback.
- Existing generation submission/uncertainty, history entry revision guards,
  private snapshots, saved image ownership and durable experiment code paths
  were inspected at their integration boundaries. Assistant writes advance the
  normal draft revision and cannot mutate an already copied run definition.
  No backend source, schema, dependencies, provider calls or scheduler changes
  are part of this follow-up.

## Verification

- Lint: PASS, `npm run lint` in `apps/web` (`eslint .`).
- TypeCheck: PASS, the same command runs `tsc --noEmit`.
- Whitespace: PASS, `git diff --check`.
- Tests: intentionally not run/added. The operator excludes frontend/helper
  automated tests and browser automation. Backend sources are unchanged, so no
  unrelated backend test rerun was performed. No paid advice/image probe,
  credential/environment read or production mutation was performed.
- Independent hash inspection confirms exact current working/build equality
  for all 23 inputs in the parent's fresh env-free locked `/novelai/` build.
  Source-map SHA-256:
  `ec4a08cbc13f1e78b80edc3c2c45da9088b54f74e93ef433b0c4979d124eddd0`.
  The reviewer made no web source edits, so the existing clean build remains
  current. Commit equality and actual public checks remain the parent's
  publication gates.
- Read-only publication review confirms baseline web/API pointer and API PID
  checks before activation, retained old hashes/releases, root-owned immutable
  assets before symlink switch, exact public HTML/asset checks, readiness/AIQQ,
  unchanged API pointer/PID afterward and guarded web fallback. There is no API
  restart or database operation in this web-only helper.

## Final source freeze

| Source | SHA-256 |
| --- | --- |
| `App.tsx` | `27479d41de0c8f1f26c07b71037f9c84dac896d6bfc99af5b21f037fc986f22c` |
| `PromptSections.tsx` | `e3e02a2a301ad956a37e3b697ad2c42e6da4847a90142fd8cdfb3017ffd461f8` |
| `SectionAssistant.tsx` | `81c72ea3630f23871e77fb3d0caea06c8823dfd907834ce600bcd6a8dfe2f8fa` |
| `api.ts` | `367680efb8901c6ffa18da59826e0c678843727f57273621670bd08f5e7c1b4c` |
| `prompt-sections.ts` | `3da0d4104277c3d0237bc0d02a883ffb6c2089677ce1f5a8b4d86afe34a2f6f7` |
| `store.ts` | `b4f2d590015cbbf531ed5ebd04e8140760fb53d7c34abfa8634824f4e99a04fe` |
| `styles.css` | `80950f188d84988ad66130993e836b7dd7247627fa572c9ad746621c0403dff0` |
