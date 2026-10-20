# Overlay Prompt Drawer Clean Build Verification

Fresh production build from an isolated temporary directory with no .env files,
explicit root inputs plus the entire source file set, clean process environment,
HTTPS locked npm sources and offline npm ci. Base path: /novelai/.

- Input count: 25.
- Source map SHA-256: 3f86e5e7dc0e8c23fbf01a3e81b746c424009fba41d6aeeb8a1b96791a489e9b.
- TypeScript and Vite production build: passed.
- No frontend/helper/browser tests or provider calls.

Assets:

- assets/index-pjwChl9j.js: 05c5445751c85d3b6de4638276d4c6fe83e12917f524443fc18b6ce3136be7c9
- assets/index-BhhmxwcB.css: d6a78670b15c0f6c6e9db612f1dad538419d7decac64578874380f529a34da10
- index.html: 17f27d595ddafecbe14e119ad41430e80ec16e87e480513e979294bd2875ab6f

Before publication verify exact working/committed/build input sets and hashes.
If independent review changes any product input, rebuild. Publish static web
resources only and retain the current API release/process and previous assets.
