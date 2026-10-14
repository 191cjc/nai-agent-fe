# Research: Prompt Weight Representation

- Date: 2026-10-14
- Scope: public source reads and the existing local draft/request data flow.
- No provider tools, browser automation, frontend tests or paid calls used.

## Syntax Evidence

NovelAI numeric emphasis uses `1.5::text::`, including negative values, on
V4 and newer image models. This differs from A1111 `(text:1.5)` notation.

- The official update URL is
  <https://novelai.net/updates?id=v4-numeric-emphasis>, linked by the
  [numeric-emphasis feature request](https://github.com/Physton/sd-webui-prompt-all-in-one/issues/364).
- Public implementation pinned to
  `zer0thgear/zer0-novel-utillities@b08e3cb45f9d8ee5a9d0ade15495791979fdf948`,
  [lib/emphasis.ts](https://github.com/zer0thgear/zer0-novel-utillities/blob/b08e3cb45f9d8ee5a9d0ade15495791979fdf948/lib/emphasis.ts),
  explicitly documents V4+ `1.5::text::`, negative weights, `{text}` times
  1.05 and `[text]` divided by 1.05. Its numeric matcher and renderer use the
  same prefix/suffix form. This is secondary source evidence, not an
  independently verified NovelAI implementation or real output check.
- Direct official documentation and update-page requests timed out from
  this host; do not claim those pages were successfully read. No undocumented
  numeric upper/lower limit is inferred from the secondary implementation.

## Local Contract

The existing request and history keep each section as a string. Preserve that
contract. Blur only switches the view; weight edits serialize the chosen
source span using numeric emphasis and update the same controlled draft field.
Default unweighted tags display 1.0. Use exact decimal arithmetic for changes
of 0.1; do not copy the reference implementation's 0.05 step or floating-point
rounding. Negative and zero numeric values remain representable.

All six currently supported native-character model IDs are V4 or newer.
Other user-entered model IDs remain possible for flat requests; show a short
V4+ compatibility hint with weight controls rather than imply older models
support numeric emphasis.

Commas/newlines delimit ordinary tags outside grouped expressions. Source
spans preserve separators, repeated tags, escapes, grouped text and original
formatting. Unknown/incomplete syntax and legacy emphasis remain visible as
original text with manual editing available, without an invented numeric
effective weight. A complete outer numeric group can retain its exact inner
text while changing only its weight prefix. Never normalize on blur or
flatten a group whose scope cannot be determined safely.
