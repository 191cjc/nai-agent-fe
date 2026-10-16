# Automatic Character Position: Fresh Build Verification

## Web Artifact

- Fresh explicit stage: /tmp/nai-auto-character-web-czmnev5x
- Copied exactly 19 source/config/lock inputs; no .env files.
- Sanitized environment and empty npm user/global config; HTTPS/integrity-verified lock.
- npm ci --offline and NAI_WEB_BASE_PATH=/novelai/ npm run build passed.
- Source map SHA-256: 2bc64a69c944ecafadd48cdf89764eb3b30633d158c05bae7ae505e33b78a70e
- All copied inputs still equal final frozen working source.
- Includes the independently reviewed App.tsx automatic/manual hint fix; the earlier private build is superseded.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-Bjw-xnGE.js | 25f2899500c7bf1757ea1b530b8a8fe69b645a0d6d4f75c809dc3e8599a7dd45 |
| assets/index-C3k99DW-.css | 1b7f9021a3989a7c4b314ed66615635348da71b8d88e79d7f12285c27160cafa |
| index.html | 53721d7a22725ea599fe74f2661d188c23868e4dc631fb8a81ea9a8c51a5d559 |

## Release Helpers

Staging requires exact equality with the final committed source and clean
build. Activation requires idle jobs/runs and a verified private online schema3
backup, then API-first readiness/OpenAPI/configuration continuity before web
publication. Public hashes, old assets and neighboring service health must
pass. Preserve private images and configuration; never restore the live DB.
Retain the new API after validation or accepted automatic-mode snapshots.

| Helper | SHA-256 |
| --- | --- |
| /tmp/nai-auto-character-build.py | 3710a0eaf71ccea299525197dadc4b59f4d234a9761944255ac06155ab123791 |
| /tmp/nai-auto-character-stage.py | a4c5519939595b57c9c8eccacc1f6aabe6817c12109de8b328d8040c245c27e0 |
| /tmp/nai-auto-character-activate.py | 1ad5bab28af7bf357ebea37e1ad2abc40e22aa5bcffa81c7854f97497804aea2 |

## Quality, Authorization and Limits

Independent full gate: 462 offline backend tests, frozen sync/lock, Ruff,
exact additive OpenAPI snapshot and web ESLint/TypeScript/source review; see
check-auto-character-position.md. Final clean build was repeated after the
checker corrected the App.tsx hint. All final input hashes match.

The operator initially prohibited restart, then explicitly authorized it with
"现在可以重启服务". Prepare and verify before publication; later deployment
evidence records actual outcomes. No paid provider calls, frontend/helper/
browser automated tests or credential changes. Actual generated appearance
and interaction remain operator acceptance.
