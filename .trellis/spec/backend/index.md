# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

The backend is the FastAPI/SQLite application under `apps/api`. Read the
applicable contracts before editing; entries marked **To fill** are still
templates and do not establish project conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | To fill |
| [Database Guidelines](./database-guidelines.md) | SQLite privacy, migrations and online backup contracts | In use |
| [Error Handling](./error-handling.md) | Error types, handling strategies | To fill |
| [Quality Guidelines](./quality-guidelines.md) | Frozen dependency checks, offline pytest, Ruff and API regression boundaries | In use |
| [Tag Provider Adapter Contract](./provider-adapter-contract.md) | Documented wire fields and offline normalization checks | In use |
| [Bounded HTTP Response Contract](./http-response-contract.md) | Shared MCP/tag raw streaming, decoded caps and cooperative deadlines | In use |
| [Browser API Contract](./api-contract.md) | OpenAPI snapshot, status responses, and secret-free browser boundary | In use |
| [Native Character Prompt Contract](./native-character-contract.md) | Structured style/shared/character prompts, native mapping and legacy history | In use |
| [Codex Advice Runtime Contract](./codex-advice-contract.md) | AiQQ-equivalent restricted turns, error mapping and cleanup | In use |
| [Host Deployment Contract](./deployment-contract.md) | Nginx/systemd routes, private storage, secrets and recovery | In use |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | To fill |

---

## Pre-Development Checklist

- Read [Quality Guidelines](./quality-guidelines.md) for backend verification.
- Read the API, provider, database, advice or deployment contract listed above
  when the change touches that boundary.
- Read `.trellis/spec/guides/index.md` and the active task's PRD/design/plan.

## Quality Check

Run the pytest, Ruff and lock-check commands in
[Quality Guidelines](./quality-guidelines.md). Review OpenAPI and its browser
consumer for API changes. Record actual execution results separately from
pending real-provider and production-host validation.

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
