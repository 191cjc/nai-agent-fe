# gpt-image-2.5-flare via relay — paid probes (2026-10-30)

Endpoint: `POST {NAI_CODEX_BASE_URL}/images/edits` (relay `https://api.airoo.cc/v1`),
`Authorization: Bearer <NAI_GPT_IMAGE_API_KEY>`, multipart form.

| # | Request | Result |
|---|---------|--------|
| 1 | 1 JPEG `image[]`, size 1024x1536, n=1, no quality | 200 in 88 s; 1 PNG 1024x1536 (~3.0 MB) |
| 2 | 2 `image[]` (JPEG + PNG), size 1024x1024, quality=medium | 200 in 98.5 s; 1 PNG (~2.9 MB); image input tokens 214→386 (both used) |

Response JSON: `{created, data: [{b64_json, revised_prompt, width, height}], usage{...}}`.
Output is PNG (`\x89PNG`), a few MB → keep the 8 MiB per-image cap.
Probe 1 kept horns, crown, outfit pattern, sandals and the katana from a complex reference.
Unverified: n>1 in one call, refusal/error body shape (assume OpenAI-style `{"error": {...}}`).
Paid probes used: 2 of 10.
