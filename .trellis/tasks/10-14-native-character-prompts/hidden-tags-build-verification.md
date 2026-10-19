# Hidden Tags Clean Build Verification

Fresh production build from an isolated temporary directory with no .env files,
explicit root inputs plus the entire source file set, clean process environment,
HTTPS locked npm sources and offline npm ci. Base path: /novelai/.

- Input count: 25.
- Source map SHA-256: d6b9e6b7a9d1e1fb4afbd41f9d36673f6cf0091ff1e6709f64f9853994ae052b.
- TypeScript and Vite production build: passed.
- No frontend/helper/browser tests or provider calls.

Assets:

- assets/index-4Z0XUfDo.js: 17cea11288dd0b8f9c3d0282abeb1ec2e54355b27b58ce4cff03afce7b394ca5
- assets/index-DSHE7A_H.css: 45fbef3fc7dcb641831c778af930431d61188f3e9d8e6beb73b19d500aa95628
- index.html: 98b75793c251b2a24bbf73e340215aa243b7fdba57431a5b68f7da289918c81d

Staging must verify the exact working/committed/build input sets and hashes.
If independent review changes product inputs, rebuild before staging.
