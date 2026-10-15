# Compact Neutral Weights — Independent Review

Date: 2026-10-15. Scope: this follow-up's two source diffs and their existing
prompt-editor/experiment callers. No source fixes were needed.

## Source Review

- `adjustPromptTagWeight` still calculates exact decimal increments of 0.1
  and delegates to `setPromptTagWeight`. Both 1.1 down and 0.9 up normalize to
  `1.0`, which now emits `artist:meion` from the corresponding numeric group.
  Explicit decimal equivalents such as `+01.000` take the same branch.
- A plain tag assigned neutral weight returns the original source unchanged.
  Numeric groups lose only their outer prefix/suffix: original body whitespace,
  escapes, nested numeric/legacy emphasis and grouped punctuation are copied
  directly from the captured source. Sibling text and separators are preserved.
  Existing unsafe-tag and stale-span guards run before the new branch;
  invalid decimal assignments still return null. Non-neutral serialization
  follows the existing unchanged paths.
- Style, shared, every independent character and global negative prompt use
  `PromptEditor` and the shared adjustment helper. Blur only records height
  and changes view state; manual-edit changes view/focus state. Neither path
  normalizes existing draft text.
- Experiment combinations call the same absolute setter, using original
  source spans in descending order. Removing a later wrapper cannot move an
  earlier span; repeated labels remain distinct occurrences. Weight metadata
  still records `1.0`, with lazy mixed-radix counts/order unchanged.
- A neutral-only dimension now budgets `tag.text.length - tag.source.length`.
  The existing exact count makes `1..1.05` by `0.1` one neutral value, so this
  case is included even though its configured maximum exceeds 1. For a
  3000-character plain style with blank shared text, the bound stays 3000;
  for a numeric outer group it decreases by that wrapper's actual length.
  Other ranges retain the conservative numeric-length upper bound. Existing
  combined-length and per-submission validation remain in GenerationStore.

These are source traces, not executed helper cases or interactive validation.

## Verification

- `env -i HOME="$HOME" PATH="$PATH" npm run lint` from `apps/web`: passed
  (ESLint and `tsc --noEmit`).
- `git diff --check`: passed.
- No frontend/helper automated tests, browser automation, paid calls, API or
  production/config/credential access. Build, release and operator interaction
  acceptance remain the main session's subsequent gates.

Source review found no unresolved issue within this follow-up. Source files
are stable and handed back to the main session for build/release.

## Main Session: Production Build

The clean production build passed in `/tmp/nai-neutral-weight-web-9uiy3st4`.
Only package.json, package-lock.json, index.html, tsconfig.json,
vite.config.ts and src were copied; the stage contained no `.env*` files.
The environment was cleared except normal PATH/HOME and explicit npm/build
settings. User/global npm config used two distinct empty files, all locked
archive URLs were HTTPS with integrity, and `npm ci --offline` preceded the
`NAI_WEB_BASE_PATH=/novelai/` build.

All 14 staged input hashes match the final working source, including the
reviewer's hashes for both changed source files. Input-map SHA-256:
`68ce8ebcfd49f7e1ccb0e4f49b9d7505926dd36b44a4bf5191c1b8c12aa89170`.
Publication will also compare these inputs against the work commit before
installing dist. Public resource checks and operator acceptance are separate.
