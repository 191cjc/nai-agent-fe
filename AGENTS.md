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

# Training-set privacy (operator rule)

Training-set content is the operator's private data. AI assistants must **never
read, open, view, decode, print, summarise or upload** it — this covers dataset
images (PNG/JPEG/thumbnails), caption `.txt` files, exported dataset zips,
reference images, and the prompt/caption text stored for dataset runs in the
production or local SQLite database and `generation-images/` storage.

- Allowed: file names, counts, sizes, checksums, timestamps, schema/column
  names, status fields and other non-content metadata.
- Debug with synthetic fixtures or the mock-based test suite, never with real
  sets. If a task truly needs to inspect content, stop and ask the operator to
  check it themselves.
- Source code, built-in prompt libraries in the repo and specs are not private.
