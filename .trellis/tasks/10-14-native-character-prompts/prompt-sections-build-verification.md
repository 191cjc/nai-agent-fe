# Prompt Sections Clean Build Verification

## Method

After frontend source freeze, copied the five explicit web build inputs and
the complete src tree into a fresh directory. The22 input files exclude all
environment files. Checked every locked npm dependency for HTTPS archives and
integrity metadata. Used empty npm config files and an explicit environment
without inherited provider/application credentials.

Ran offline npm ci, then npm run build (TypeScript and Vite) with the sole
application build setting NAI_WEB_BASE_PATH=/novelai/. No frontend/helper tests,
browser automation or provider calls were run. The existing esbuild install
script advisory did not prevent the successful build.

## Result

Frozen-source build passed on2026-10-16. Final independent full affected-layer
review passed with no web source correction; this build remains current.
Committed-input equality is verified again by release staging before activation.

- Inputs:22 files.
- Source-map SHA-256:
  `707ef10e4b524ea2e64314b6d7ca4a757504b5b93ab0faeb8db54faff2548c57`.
- index.html:
  `5aaa23db0660c50e407f95abbba0a78c550b82c67551f197f312f94fbd1de9b3`.
- assets/index-ChalmHOz.js:
  `afda0e9ac5526392f65e6d882d4d730ef8c082314a260ba0fc94c2ade0c1bd06`.
- assets/index-COhywvsg.css:
  `42f95d5174a52897e05f815ce45dec0111023c85ff2f7d1f16af7a3243b990c8`.

This verifies static build output only. Interactive desktop/mobile behavior
and resulting provider images remain operator acceptance.
