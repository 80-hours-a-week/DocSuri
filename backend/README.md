# backend/ — modular monolith app-shell (deploy unit ①)

> **Owner:** @revenantonthemission (Track 2, app-shell — CODEOWNERS `/backend/`) · **Runtime:** Python (§5-A)
> **Status:** 🟢 app-shell scaffold — boots with zero infrastructure; mounts modules as they land.

The **app-shell** is the bootstrap·router·DI·common-middleware wiring that hosts the backend
modules (U2 discovery, U3 accounts, U4 library) and the U6 gateway middleware in **one
FastAPI runtime**. It is the single entrypoint for deploy unit ①.

## ⚙️ CG-1 resolved — framework = FastAPI

The backend web framework was an open app-shell decision (`CG-1`, noted in the discovery and
accounts modules as "pending @ELSAPHABA sign-off"). App-shell ownership moved to **Track 2**
in **PR #42**, so the app-shell owner (@revenantonthemission) resolves CG-1: **FastAPI**.
Both modules already targeted FastAPI, so nothing in their code changes.

## Why it mounts modules *optionally*

The shell imports each module **lazily** and **skips** any that isn't present, logging the
reason (see `wiring.py`). This is deliberate:

- The shell can merge to `develop` **before** the track PRs (#39 discovery, #41 accounts).
- Each track PR then merges into its clean lane and **auto-wires** with no shell change.
- A broken/absent module degrades to a skip — it never sinks the whole backend.

`GET /readyz` reports what actually mounted, so you can watch modules light up as PRs land.

## Layout

```
backend/
├── __init__.py        # package marker (version)
├── main.py            # ASGI entrypoint: `app = create_app()`
├── app.py             # create_app() factory + lifespan + middleware (CG-1: FastAPI)
├── config.py          # env-driven Settings (SQLite/no-Redis defaults → boots bare)
├── db.py              # SQLAlchemy engine/session seam (fills accounts' get_db_session)
├── errors.py          # fail-closed, no-leak error handler (SEC-9/SEC-15)
├── health.py          # /health · /healthz · /readyz
├── wiring.py          # module registry — optional mount of accounts (U3) & discovery (U2)
├── modules/           # ⬇ module lanes (each owned by its track)
│   ├── accounts/      #   U3 (Track 2) — mounted from PR #41
│   ├── library/       #   U4 (Track 2) — later
│   └── discovery/     #   U2 (Track 3) — docsuri-discovery pkg, imported as `discovery`
├── middleware/        # U6 gateway (Track 1, @ELSAPHABA) — authn/authz/rate-limit/grounding
├── pyproject.toml     # docsuri-backend deps (shared·fastapi·sqlalchemy·redis)
├── docker-compose.yml # full-local Postgres + Redis profile (optional)
└── .env.example       # configuration surface
```

## Run / test

```sh
cd backend
uv sync                     # fastapi·sqlalchemy·redis·docsuri-shared(path)
uv run pytest               # app-shell smoke + contract tests (no services needed)
uv run ruff check .

# serve (run from the REPO ROOT so `backend.*` imports resolve):
cd .. && uv run --project backend uvicorn backend.main:app --reload
```

The shell boots with **no DB/Redis**: `/health` is dependency-free and modules are optional.
For the full local stack (accounts needs Postgres + Redis):

```sh
docker compose -f backend/docker-compose.yml up -d   # postgres:5432, redis:6379
export DATABASE_URL=postgresql+psycopg://docsuri:docsuri@localhost:5432/docsuri
```

## Module integration seams

| Module | Idiom | Shell wiring |
|---|---|---|
| **accounts** (U3) | exposes `controller.router` + `get_db_session` seam + `SessionRepository` singleton | override `get_db_session` → SQLAlchemy session; close the Redis pool on shutdown |
| **discovery** (U2) | exposes factories `build_mock_orchestrator()` + `build_router(orch, hook)` | build the mock bundle, mount the returned router (mock-first; real adapters/U6 hook swap in later) |

## Assembly (when all tracks are present)

`docsuri-discovery` is a self-contained package under `modules/discovery/` imported as the
top-level `discovery`. It is **not** declared in `pyproject.toml` here (its path doesn't exist
on `develop`). The assembled backend installs it (`uv pip install -e modules/discovery`); the
shell then mounts it automatically. accounts is an in-tree `backend.modules.accounts` package
and runs on the shell's declared deps — no separate install.

## Boundaries

- `backend/middleware/` (U6) is **@ELSAPHABA / Track 1** — the shell leaves a seam (CORS,
  request-id, generic error handler are app-shell concerns; authn/authz/rate-limit/grounding
  are U6's). Don't implement U6 logic here.
- Modules own their `modules/*` lane; the shell never reaches past the documented seam.
