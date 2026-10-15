# Web workspace

Use Node 20+ and run `npm install` in `apps/web`. Start the API on
`127.0.0.1:8000` with `NAI_PUBLIC_ORIGIN=https://localhost:5173`, then run
`npm run dev` here and open `https://localhost:5173`. Vite serves HTTPS with
a local development certificate and proxies same-origin `/api/*` to the API.
Trust the development certificate in your browser when prompted; plain HTTP
cannot carry the API's Secure session cookie. The API's origin check must match
the browser URL exactly, including the port. Vite holds port 5173 by default
so it cannot silently select an origin that does not match the API setting.

Generated images are stored privately on the server for seven days; history
preserves parameters and experiment groups. Refresh/restart can reopen retained
images for comparison without resubmitting paid generation.
The positive editor separates style, shared scene text and up to six native
character descriptions. The negative editor opens in the same content area
from its compact side tab. Tag insertion has an explicit positive destination;
history reuse restores the separate sections and characters, while older flat
prompts populate shared text. Native characters require a compatible API and
V4/V4.5/V5 model; deploy the API before this frontend. See
`../../.trellis/spec/backend/native-character-contract.md` for the exact
supported-model subset and draggable normalized character coordinates.

Production builds can set `NAI_WEB_BASE_PATH=/novelai/`. The browser then calls
`/novelai/api/*`; the reverse proxy strips `/novelai` before forwarding to the
backend's `/api/*` routes. `NAI_PUBLIC_ORIGIN` remains the HTTPS origin only.

Style experiments run on the server after one explicit Start. Failed groups
are recorded and skipped; only explicit Stop prevents later groups. Closing
or refreshing the page and logging out detach the UI without stopping the run.
Login/reentry reconnects to the same active run; progress shows successes,
failures and the fixed effective seed. Historical comparisons load one image
at a time and never resubmit generation. No automatic retry of a failed group.
