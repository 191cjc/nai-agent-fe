# Production Deployment: Latest History and Left Tool Drawers

- URL: <https://www.firesoul.cn/novelai/>.
- Source: `5b48196cbbe143bef628bceada2f859f9b75947e`.
- Web release: `/srv/www/novelai/releases/20261015T093934`.
- Previous web retained: `/srv/www/novelai/releases/20261015T092041`.
- API unchanged: `/srv/novelai/releases/20261015T082138`, PID `3098684`, active.

Authenticated entry now restores the newest parameter-history item once
through existing reuse semantics, with session, draft-edit and generation
ownership guards. Settings/history/prompt lookup/advice now share the left
drawer area. Hidden panels stay mounted; the bottom tool drawer and its
reserved height are removed. No generation, API or image ownership changed.

Independent combined review found no defects; ESLint/TypeScript and diff/
context checks passed. See `check-history-and-drawers.md`. Fresh explicit-
input env-free build passed; all 14 inputs matched reviewed working source
and the published commit. See `history-and-drawers-build-verification.md`.
Input-map SHA-256: `cafd1e3c26ce88ba2731bd1d1e87e9c5aebe523713827204d6d7c8c2f623debd`.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-C5ONU_2_.js | `cf3b1def1608c07f96af790b274dfd5df499465cd6d7eaac4a887316e6a50b97` |
| assets/index-C8_iA6T1.css | `5c63e36aa087328744b71f95df1d8bb6a75f39b58966f15d76ac7e2d4e7f4800` |
| index.html | `c87c9389eb000f5891b85bc7c7fd0b09e90aad394b759860cd9b91d5aedf2802` |

Only dist was published, root-owned, directories 0755/files 0644. New shared
assets passed public HTTP/hash checks before atomic web switching. Public
HTML and its exact JS/CSS references then matched expected hashes with 200.
API readiness returned `status=ok`, `/aiqq/health` returned 200, and previous
assets retained their public hashes. Previous releases/assets remain. Web
rollback restores the previous web pointer with the API unchanged.

No API restart, migration, Nginx/configuration edit, credential access/change,
browser persistence, frontend/helper automated tests, browser automation or
paid calls occurred. Static review/build checks do not replace operator
desktop/mobile, keyboard and actual-provider acceptance; broader task remains
active. Existing browser-local images should be downloaded before refreshing.
