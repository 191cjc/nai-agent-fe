# Experiment Viewer Build Verification

- Fresh stage: `/tmp/nai-experiment-viewer-web-qf2kselz`.
- Explicit web inputs only; no `.env*` files or inherited build variables.
- Distinct empty user/global npm configs, HTTPS registry and locked HTTPS
  archives with integrity; `npm ci --offline` passed.
- `NAI_WEB_BASE_PATH=/novelai/ npm run build` passed (TypeScript + Vite).
- All 14 staged source inputs match working source.
- Input-map SHA-256: `24454e116d60b3ae0e018761cdd738c2d0f4b310aedf5d781805fcf533773ecc`.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-hmQKDWQV.js | `019a1914506084ab21ffc45dec7aeea69d78a6d86e894a197a0adef88fa8a3c5` |
| assets/index-n8D8xr3P.css | `b1985c0c0b6353cc48eeefcef39cdc2bb3e50f00775a032e90ef40d34aff3f3c` |
| index.html | `4bcb030a93a2d382479ffaa965f762f9da1499bed1556ca0ec0063e01d0ec2c6` |

The publication guard must also match every staged input against the work
commit before switching. Independent source review and interactive operator
acceptance are separate from this static build. No frontend/helper automated
tests, browser automation or paid provider calls were run.
