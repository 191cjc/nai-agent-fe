# Web workspace

Use Node 20+ and run `npm install` in `apps/web`. Start the API on
`127.0.0.1:8000` with `NAI_PUBLIC_ORIGIN=https://localhost:5173`, then run
`npm run dev` here and open `https://localhost:5173`. Vite serves HTTPS with
a local development certificate and proxies same-origin `/api/*` to the API.
Trust the development certificate in your browser when prompted; plain HTTP
cannot carry the API's Secure session cookie. The API's origin check must match
the browser URL exactly, including the port. Vite holds port 5173 by default
so it cannot silently select an origin that does not match the API setting.

Generated images are temporary; history stores parameters only.
Production builds can set `NAI_WEB_BASE_PATH=/novelai/`. The browser then calls
`/novelai/api/*`; the reverse proxy strips `/novelai` before forwarding to the
backend's `/api/*` routes. `NAI_PUBLIC_ORIGIN` remains the HTTPS origin only.
