<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

# Database and training-set privacy (operator rule)

Real database contents and generated training-set contents are the operator's
private data. AI assistants must **never read, open, view, decode, print,
summarise or upload their concrete content or images**. This applies to local,
production and remote storage, including copies, backups and exports.

- Protected database content includes stored prompts, captions, prompt
  snapshots, run definitions, recipe values, generation settings, provider
  request payloads and authentication data. Do not inspect actual record
  values or raw SQLite, WAL/SHM, backup or dump contents.
- Protected training-set content includes generated images (PNG/JPEG and
  thumbnails), reference images, caption `.txt` files, exported dataset zips
  and their contents, including files in `generation-images/`,
  `reference-images/` and training/export staging directories.
- Do not access this content indirectly through scripts, tools, delegated
  agents, browser previews, API responses or logs. Do not dump tables, sample
  real records, extract archives, preview images, perform OCR or decode image
  data to understand the data format.
- Allowed: file names, counts, sizes, checksums, timestamps, schema/table/column
  names, status fields and other non-content metadata only. Any inspection
  must exclude private text, payloads and image bytes.
- **Understand formats through code**: read SQL migrations, models, type
  definitions, serializers, export code and specs instead of real records or
  generated datasets.
- Debug and verify with synthetic fixtures, disposable test databases populated
  only with synthetic data, or the mock-based test suite, never with real sets
  or database records. If a task truly needs content inspection, stop and ask
  the operator to check it themselves.
- Source code, built-in prompt libraries in the repo, specs and synthetic test
  fixtures are not private training-set content.
