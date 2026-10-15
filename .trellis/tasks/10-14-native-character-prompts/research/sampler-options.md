# Research: Sampler Choices

Date: 2026-10-15. Public pinned source only; no provider calls or credentials.

The current settings UI has a free-form sampler input with no suggestions.
The browser/API contract intentionally keeps sampler a bounded string. The
previously collected deployed MCP schema also exposes a nullable string,
not an enum, so frontend choices must not become a new backend restriction.

Public provider commit `49554a12938ed33856dbd8a9ce11db5f41704123`
defines these exact values in `nai/constants.py`, lines 61–68:

| Display name | ID |
| --- | --- |
| Euler | `k_euler` |
| Euler Ancestral | `k_euler_ancestral` |
| DPM++ 2S Ancestral | `k_dpmpp_2s_ancestral` |
| DPM++ 2M | `k_dpmpp_2m` |
| DPM++ 2M SDE | `k_dpmpp_2m_sde` |
| DPM++ SDE | `k_dpmpp_sde` |
| DDIM | `ddim_v3` |

[Pinned enum source](https://github.com/xinvxueyuan/NovelAI-Image-MCP/blob/49554a12938ed33856dbd8a9ce11db5f41704123/apps/server/src/novelai_image_mcp/nai/constants.py#L61-L68).
The raw-content host timed out; the GitHub contents API returned the pinned
file successfully. No account/model compatibility or visual-output guarantee
is established by this source read.

Use an actual select with human names and IDs, plus an explicit manual-entry
mode. Keep unknown historical IDs and typed IDs losslessly. Do not choose a
new default, coerce values during render/reuse, add an API enum, or change the
generation/provider flow. Local UI state selects manual editing; the existing
draft string remains the sole submitted value. Existing select styles suffice.
