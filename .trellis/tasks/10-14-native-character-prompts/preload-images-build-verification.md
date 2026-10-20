# Experiment Image Preload Clean Build Verification

Fresh production build from an isolated temporary directory with no .env files,
explicit root inputs plus the entire source file set, clean process environment,
HTTPS locked npm sources and offline npm ci. Base path: /novelai/.

- Input count: 25.
- Source map SHA-256: daba1226cb15e3775accd39d16d00a68c28c8adc800bf56a409c10f65d804a51.
- TypeScript and Vite production build: passed.
- No frontend/helper/browser tests or provider calls.

Assets:

- assets/index-Ck8KXK4E.js: bcb22e81f346ec3d55d4801716f0f9e017b0ec0bf7136b10b3fc98249c0b7c7b
- assets/index-CfyDuHQQ.css: 9139441f0212e5ded860914a8e97e8a9a5e3584b37fd0beb4f74900f16187ee7
- index.html: 62db4fb553e9274a6d091bd95dceb79d42c9d9599895807aeed233cb9c645407

Staging must verify the exact working/committed/build input sets and hashes.
If independent review changes product inputs, rebuild before publication.
Publish only static web resources and retain the current API release/process.
