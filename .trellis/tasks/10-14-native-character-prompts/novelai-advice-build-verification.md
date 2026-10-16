# NovelAI Advice Clean Build Verification

Fresh explicit25-input env-free locked web build succeeded for /novelai/.
No environment files or provider credentials loaded.

- ESLint/TypeScript passed during implementation; final independent gate is
  recorded in check-novelai-advice.md.
- npm ci --offline and TypeScript/Vite production build passed.
- Exact working/build input sets and each hash match; stage also enforces
  committed source equality before publication.
- Build source map SHA-256: `e00d6b5fecb3dbd18acefd8270035ebe333729841b432084eaf028f988168ba7`.
- Stage: /tmp/nai-novelai-advice-web-92p41jnz.
- No frontend/helper/browser automated tests or live model/account probes.

| Artifact | SHA-256 |
| --- | --- |
| assets/index-BF0HcGj9.css | `881d84410445bb2ee6afbb23829c6bac84f12d0db2285febf93035125fab891c` |
| assets/index-CnnrEROx.js | `65c0e7add119841891525dadc14ac2933d7f66dfb9038f14da9e80ea0ebed4a1` |
| index.html | `d802dcd3d0f436a5b76dc358652cfe815e1a28a5aebc811c26835278b3dc4361` |
