# Implementation: Style Experiment

1. Research the existing generation lifecycle and retain the shared API,
   immutable snapshot, seed and URL-ownership evidence.
2. State/helper implement agent owns store.ts, style-experiment.ts and
   prompt-weights.ts. Follow the shared interfaces in style-experiment-design.
   Keep generation orchestration in its current owner; coordinate types with
   UI agent. Do not modify App.tsx/CSS or run frontend tests/browser checks.
3. UI implement agent owns StyleExperiment.tsx, App.tsx and styles.css. Use the
   agreed types and commands; no direct API/polling/URL creation in components.
   Preserve existing tag editor, independent characters and normal results.
4. Independent full-scope check agent reviews/fixes all follow-up changes,
   especially state races, lazy decimal enumeration and image ownership. Run
   ESLint/TypeScript and source review; do not run frontend automated tests.
5. Main session captures executable contracts, validates context/diffs, builds
   fresh env-free inputs, commits, publishes web-only and verifies page/assets/
   readiness plus the existing neighboring service. Record release/journal.

## Progress

- [x] Research and bounded frontend-only architecture recorded.
- [x] Exact range/combination helper and sequential generation state.
- [x] Style-heading entry, configuration, progress and comparison gallery.
- [x] Independent full-scope source review; ESLint/TypeScript. No concrete
  defects found; see `style-experiment-verification.md` for lifecycle evidence.
- [x] Clean env-free production build and reviewed working-source comparison;
  see `style-experiment-build-verification.md`. Publication also verifies the
  staged input map against the final work commit.
- [ ] Web-only deployment and public HTTP/hash checks.
- [ ] Operator desktop/mobile/keyboard and actual-provider acceptance.
