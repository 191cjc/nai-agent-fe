# Latest History and Left Drawers Build Verification

- Fresh explicit-input stage: `/tmp/nai-latest-history-web-b8z_ds32`.
- No `.env*` files; clean build environment with distinct empty npm configs.
- Lockfile archives use HTTPS and integrity; `npm ci --offline` passed.
- `NAI_WEB_BASE_PATH=/novelai/ npm run build` passed (TypeScript + Vite).
- All 14 staged source inputs match working source.
- Input-map SHA-256: `cafd1e3c26ce88ba2731bd1d1e87e9c5aebe523713827204d6d7c8c2f623debd`.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-C5ONU_2_.js | `cf3b1def1608c07f96af790b274dfd5df499465cd6d7eaac4a887316e6a50b97` |
| assets/index-C8_iA6T1.css | `5c63e36aa087328744b71f95df1d8bb6a75f39b58966f15d76ac7e2d4e7f4800` |
| index.html | `c87c9389eb000f5891b85bc7c7fd0b09e90aad394b759860cd9b91d5aedf2802` |

Publication must match these inputs against the reviewed work commit before
the switch. Static builds do not establish interactive browser acceptance.
No frontend/helper automated tests, browser automation or paid calls ran.
