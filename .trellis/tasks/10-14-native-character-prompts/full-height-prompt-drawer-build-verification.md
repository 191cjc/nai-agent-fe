# Full-height Prompt Drawer Clean Build Verification

Fresh25-input production build in an isolated temporary directory with no
.env files, explicit root inputs plus the entire source file set, a clean
environment, HTTPS locked dependencies and offline npm ci. Base: /novelai/.

- TypeScript/Vite production build passed.
- Source map SHA-256: 5eb83e711d38f7426b07aa99807f8e7b799eb70420ee603c99f4a7ed68935608.
- assets/index-B-f8L83D.js: 05c5445751c85d3b6de4638276d4c6fe83e12917f524443fc18b6ce3136be7c9
- assets/index-CKIi-c3G.css: 67fd1507fb5839d78c819d63ba67a4abbfb1bbacd45b7b430bd2e1aa5fc1abed
- index.html: 00ce53061e44270dec2a94af1724305cda753207887243eb0c2b8222b65c9cec

Independent review made no source edits. Publication must match exact working,
committed and build input sets/hashes, retain old assets and preserve the API
release/process. No frontend/helper/browser tests or provider calls.
