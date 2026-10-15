# Production Deployment: Experiment Image Navigation

- URL: <https://www.firesoul.cn/novelai/>.
- Source: `1f9045d506444c9fcebf6c9ce3034f0bb8fd9b81`.
- Web release: `/srv/www/novelai/releases/20261015T092041`.
- Previous web retained: `/srv/www/novelai/releases/20261015T082138`.
- API unchanged: `/srv/novelai/releases/20261015T082138`, PID `3098684`, active.

Style-experiment comparisons now show one contained image with side arrows
and viewer-scoped left/right keys. Browsing follows group/image order, retains
weights/seeds/parameters/downloads and failure placeholders, and keeps the
current image selected as new results arrive. No generation or archive
ownership behavior changed.

Independent source review found no defects; ESLint/TypeScript and diff
checks passed. See `check-experiment-viewer.md`. The fresh explicit-input,
env-free offline build passed; all 14 staged inputs matched reviewed working
source and the published commit. See `experiment-viewer-build-verification.md`.
Input-map SHA-256: `24454e116d60b3ae0e018761cdd738c2d0f4b310aedf5d781805fcf533773ecc`.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-hmQKDWQV.js | `019a1914506084ab21ffc45dec7aeea69d78a6d86e894a197a0adef88fa8a3c5` |
| assets/index-n8D8xr3P.css | `b1985c0c0b6353cc48eeefcef39cdc2bb3e50f00775a032e90ef40d34aff3f3c` |
| index.html | `4bcb030a93a2d382479ffaa965f762f9da1499bed1556ca0ec0063e01d0ec2c6` |

Only dist files were installed, root-owned, directories 0755/files 0644.
New shared assets passed HTTP/hash checks before the atomic web switch.
Public HTML and its exact JS/CSS references then matched the expected hashes
with HTTP 200. API readiness returned `status=ok`; `/aiqq/health` and the
previous assets returned HTTP 200 with retained hashes. Old releases/assets
remain; web rollback restores the previous web pointer with the API unchanged.

No API restart, migration, Nginx/configuration edit, credential access/change,
frontend/helper automated tests, browser automation or paid calls occurred.
Interactive desktop/mobile/keyboard and actual-image acceptance remains with
the operator; the broader task stays in progress. Existing comparison images
remain browser-local and are lost on refresh, so download before reloading.
