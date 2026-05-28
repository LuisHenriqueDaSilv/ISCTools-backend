# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Before starting any task, read the rule files in `.agents/` and `.agentes/`. They contain the architectural decisions that must be followed throughout the codebase.

## Repository layout

The root is reserved for cross-cutting concerns (docs, agent rules, CI config). All application code lives under `app/`.

```
backend/
├── .agents/                          ← rules for AI agents (read before any task)
├── .agentes/                         ← rules for AI agents (read before any task)
├── app/                              ← all runnable code
│   ├── src/
│   │   ├── main.py                   ← FastAPI app + router registration
│   │   ├── core/                     ← shared infra (config, database)
│   │   ├── auth/                     ← authentication module
│   │   └── chat/                     ← AI chat module
│   ├── alembic/                      ← migrations
│   ├── docker-compose.yml
│   └── Makefile
└── CLAUDE.md
```

## Commands

All `make` commands must be run from the `app/` directory.

```bash
cd app

make up                          # build images and start containers (API + Postgres)
make down                        # stop containers
make logs                        # tail API logs

make migration name="<slug>"     # generate autogenerate migration (containers must be up)
make migrate                     # apply all pending migrations
make rollback                    # downgrade one migration
```

The API runs on `http://localhost:8000`. Interactive docs at `/docs`.

## Architecture

Each domain is a self-contained module under `src/` with a fixed set of files: `models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`. See `.agents/` and `.agentes/` for the full rules.

### Layer contract

The most important invariant spans three files in every module:

- **`repository.py`** — only layer that touches `Session`. Returns ORM objects or `None`. No business logic, no exceptions.
- **`service.py`** — raises `ValueError` for domain errors. No knowledge of HTTP (`HTTPException`, status codes, `Request` are forbidden here). Receives `db: Session` as a plain argument passed down from the router.
- **`router.py`** — catches `ValueError` and converts to `HTTPException`. Injects `db` via `Depends(get_db)`.

### Adding a new module

Three wiring steps are mandatory or the app/migrations will silently break:

1. Import the new `models.py` in `alembic/env.py` (required for autogenerate to detect the tables).
2. Register the router in `src/main.py` with `app.include_router(...)`.
3. Run `make migration name="add_<module>"` and `make migrate`.

### Pending TODOs

- `src/auth/service.py` — password must be hashed before storing (plain text currently).
- `src/chat/service.py` — AI provider call is a placeholder returning a hardcoded string.

### Environment

`src/core/config.py` reads from `.env` via `pydantic-settings`. Only `DATABASE_URL` is a required field; other vars in `.env` (Postgres credentials) are passed directly to Docker and ignored by the Settings class (`extra = "ignore"`).
