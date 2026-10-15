# Production Deployment: Draggable Character Positions

- URL: <https://www.firesoul.cn/novelai/>.
- Source: `31cff3e16c3deebca94fb0866d360c5e0d6433ae`.
- Paired release: `20261015T101355`, API `/srv/novelai/releases/20261015T101355`
  and web `/srv/www/novelai/releases/20261015T101355`.
- API PID: `3125676`; active and working directory matches the new release.
- Previous API `20261015T082138` and web `20261015T093934` retained.

Numbered character markers now drag in a canvas-proportioned preview, with
explicit overlap selection, marker-focused arrow adjustment and center reset.
Validated x/y flow to the provider and existing private parameter history;
reuse/latest-entry restoration retain them and experiments freeze them at
Start. Old native JSON defaults to center. Only nonblank characters submit.

Independent full-scope review found no defects. All 249 offline backend tests,
Ruff, frozen sync/lock checks, frontend ESLint/TypeScript and a fresh env-free
production build passed. See `check-character-positions.md` and
`character-positions-build-verification.md`. All 15 web and 19 API source inputs
matched the reviewed work commit and staged bytes before activation. Pinned
production CLI probe returned `codex-cli 0.152.1`; provider-free staged OpenAPI
import created no database.

- API source-map SHA-256: `3b4314871d2b3a0da97c0173b44c9b2e40d45809586e8ae60f31af311b433034`.
- Web source-map SHA-256: `d858a87900ec88366fda9381a7772fcbe19684fcc67f2842a95abc4009dd2c7f`.
- Reviewed OpenAPI file SHA-256: `0b8410b3f9d73ad1648bbecfdaca03735a61fdf4de1dd6150c1400b82f7c6951`.

| Artifact | SHA-256 |
| --- | --- |
| index.html | `39b52605d3617ad7d821b49d67780e243295d9dbddd989f206b194bf4654fac2` |
| assets/index-C6LuZHs6.js | `5d1843c99380b12b83acc848c5a64054eaa8efd55bb7fa5bab24cacf13cfb54a` |
| assets/index-_JAKkl6U.css | `355df73cb24a7dfa94b726052566f10ea81938dcaac5056151550b9ccbf9be79` |

## Activation Evidence

- Existing configuration bytes and NAI/provider process environment stayed
  identical; no configuration edit, credentials replacement or source env load.
- Service-user SQLite online backup copied privately to
  `/var/backups/novelai/20261015T101355-character-positions/novelai.sqlite3`.
  Copy hashes matched, integrity_check returned ok, private directory 0700 and
  root-owned snapshot 0600. SQLite schema remained version 2.
- Active jobs were zero before restart and after service stop. API switched
  first, then readiness and exact running OpenAPI matched the reviewed schema.
- Only immutable dist files were published, root-owned and readable. New shared
  assets passed public HTTP/hash checks before the atomic web switch. Public
  HTML and exact JS/CSS references then matched the expected SHA-256 values.
- Public readiness returned status=ok; `/aiqq/health` returned 200. Previous
  assets remained publicly accessible with unchanged hashes; previous release
  directories remain available.

If reverting the web, retain the coordinate API for new pages already open.
The earlier API hardcodes center and would silently ignore their positions.
No DB restore is needed. API restart discarded the earlier process's transient
image cache; parameter history remains durable.

No Nginx/unit changes, paid provider calls, frontend/helper automated tests or
browser automation. Static/source/build and release checks do not replace
operator desktop/mobile, keyboard and actual-provider placement acceptance.
The broader task remains in progress for those checks.
