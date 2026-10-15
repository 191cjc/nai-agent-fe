# Production Deployment: Compact Neutral Weights

- URL: <https://www.firesoul.cn/novelai/>.
- Source: `15f88d04e614e2bc10cfea2a8a405c2e6ddd6a63`.
- Web release: `/srv/www/novelai/releases/20261015T073652`.
- Previous web retained: `/srv/www/novelai/releases/20261014T101427`.
- API unchanged: `/srv/novelai/releases/20261014T085902`, PID `2754998`, active.

Explicit exact-neutral assignments now remove only the selected outer numeric
wrapper: 1.1 down or 0.9 up produces `artist:meion` at displayed weight 1.0.
All prompt fields and style experiments share this behavior. Plain neutral
tags remain unchanged; neutral-only experiments budget their compact length.

Independent review found no defects; ESLint/TypeScript, context validation
and `git diff --check` passed. See `neutral-weight-verification.md` for source
traces and the explicit-input, env-free, locked offline production build.
All 14 staged input hashes matched both reviewed source and the work commit
before publication. Input-map SHA-256:
`68ce8ebcfd49f7e1ccb0e4f49b9d7505926dd36b44a4bf5191c1b8c12aa89170`.

| Artifact | SHA-256 |
| --- | --- |
| index.html | `0ef58f60691b7ae7ccdbc281b3f6ec65c6029ff0863c0ed509ce98849c48058a` |
| assets/index-AOY7WPOn.js | `c2f1a9937eb57eb11deaf802b088694c3f719f9b31ffe5347f3cedcaba8f01df` |
| assets/index-Z5ORKZap.css | `08e9f85026548ffe3b5c08a343e0ebb78caff6357d403fcb410c90d271587941` |

Only dist files were installed, root-owned, directories 0755/files 0644.
Shared immutable assets were HTTP/hash-verified before the atomic web switch.
The public HTML and its actual JS/CSS references then matched the above
hashes with HTTP 200; API readiness returned `status=ok`, `/aiqq/health`
returned 200, and previous assets retained their exact hashes. All prior
releases/assets were preserved. Rollback can atomically restore the previous
web pointer without changing the API; no rollback was necessary.

No API restart, schema migration, Nginx/configuration edit, credential change,
direct database access, paid call, frontend/helper automated test or browser
automation occurred. Interactive/provider acceptance remains with the
operator, so the broader active task remains in progress.
