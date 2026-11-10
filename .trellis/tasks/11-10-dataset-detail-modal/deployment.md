# Frontend-only publication

The operator explicitly requested immediate frontend publication and excluded
backend publication or other changes that could affect running tasks.

- Public URL: https://www.firesoul.cn/novelai/
- Work commit: `02c5dab92cb539d6745eb4ca073cce0b3fc70069`
- Web release: `/srv/www/novelai/releases/20261110T135850Z-02c5dab`
- Previous web release, retained: `/srv/www/novelai/releases/20261107T142121Z-8499310`
- Published at: 2026-11-10 21:58:50 Asia/Shanghai.
- Verification completed (UTC): 2026-11-10T14:00:42.123602+00:00.

## Published scope

Only the built static HTML/JS/CSS bundle was copied to a new web release.
New immutable shared assets were installed before the atomic web `current`
symlink switch. Existing shared files and the prior release were retained.
No API code/release/configuration, Nginx configuration, systemd service,
private database/image storage, durable runs or GPU-training jobs were changed.
No service restart, migration, provider request or real dataset inspection ran.

## Build and verification

- Exact web source sets and all 46 input hashes matched the
  committed tree, working tree and isolated staging directory. No `.env*` was
  copied. HTTPS/integrity validation covered 229 locked package archives.
- Clean-environment locked `npm ci` and `/novelai/` production build passed.
  Source was unchanged from the reviewed lint/type-check gate. The build's
  large-main-chunk advisory was nonblocking.
- All 11 newly published files matched their staged SHA-256 over
  public HTTPS, including the lazy ReviewGrid chunk. HTML has no-cache headers;
  hashed assets have immutable cache headers.
- Two prior entrypoint assets still matched over public HTTPS. All
  234 previously shared asset hashes remained
  unchanged locally.
- Public and loopback readiness endpoints returned HTTP 200 before and after.
- API release stayed `/srv/novelai/releases/20261107T142121Z-8499310`.
- API MainPID stayed `2882060`; its monotonic start
  timestamp remained `7991247093154`.
  ActiveState/SubState remained active/running.
- Nginx snippet SHA-256 was unchanged. No reload was needed.
- Temporary build/dependency staging was removed after verification.

Selected public artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| `assets/ReviewGrid-B85Tk380.js` | `74d168185a4fde77383cade8f5c75e7a2df0a2d5a999e66f41bd27993748ba54` |
| `assets/index-Bbzb6OlB.js` | `03c09b4e3e53bb1912f839506965e2df924cf258b857efa2adad503ad69c1648` |
| `assets/index-so_EZpMA.css` | `b1bfe27b271550374e679aafab3c5311609a1ee8d2a23d6e582dfea923c0f0f2` |
| `index.html` | `8328cb6cb8e53bc4b1e306ddcbd9496cd51f00e31f84e3742b07060cd09d57a5` |

## Rollback and remaining acceptance

A frontend rollback can atomically repoint only the static web symlink to the
retained previous web release; it must leave the API and shared assets intact.
No rollback was required. Interactive browser acceptance remains with the
operator under the project restriction on automated/browser tests.
