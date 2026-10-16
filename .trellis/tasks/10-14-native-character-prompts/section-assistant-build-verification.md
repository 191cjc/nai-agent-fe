# Per-section Assistant Clean Build

## Method

Copied the five explicit web root build inputs and complete src tree into a
fresh directory after implementation source freeze. The23 input files exclude
environment files. Validated locked HTTPS npm archive URLs/integrity and used
empty npm configuration plus an explicit process environment without inherited
application/provider configuration.

Ran npm ci --offline, then npm run build (TypeScript + Vite) with
NAI_WEB_BASE_PATH=/novelai/. Build passed. The existing esbuild install-script
advisory was non-blocking. No frontend/helper/browser automated tests or paid
provider probes were performed.

## Artifacts

- Source inputs:23 files; source-map SHA-256:
  `ec4a08cbc13f1e78b80edc3c2c45da9088b54f74e93ef433b0c4979d124eddd0`.
- index.html:
  `3ca3e2ea246b1a11177300bf7c9f75daeb5721531546c5ee2a87b2a7fc0ed742`.
- assets/index-D0C4bTbk.js:
  `751e9590f81f15764bc98f1527431f5c8d3904933c671d80f676eb7e2cf2f258`.
- assets/index-CXbEg6OA.css:
  `7593889896ae76feef3d6d6172cb561da607abee621d93d3bf41c724929bb416`.

Independent final full affected-frontend review passed with no source fixes.
All23 final source inputs match this clean build; no rebuild required.
Publication also verifies exact input-set equality across committed/working/
build trees and each input SHA-256. Source checks establish static behavior
only; interactive and actual service-result acceptance remain operator checks.
