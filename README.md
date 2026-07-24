# AI Customer Feedback Intelligence Platform

AI-powered customer feedback intelligence system (FastAPI, OpenAI, RAG,
PostgreSQL + pgvector). See `AI_Customer_Feedback_Intelligence_Architecture.md`
in the repo root for the full architecture.

## Database: one shared Postgres for both local dev and Docker

Docker Compose's `db` service (`pgvector/pgvector:pg17`) publishes port
`5432` to your host, so it's the single source of truth for both a local
`uvicorn` run and the containerized app — no separate local Postgres
install needed, and no data drift between "running it locally" and "running
it in Docker."

```bash
cd feedback-intelligence-platform
cp .env.example .env   # then fill in OPENAI_API_KEY at minimum
docker compose up -d db   # just the shared database, exposed on localhost:5432
```

### Option A: Local dev (venv + shared Docker database)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/dashboard, or verify the API directly:

```bash
curl http://127.0.0.1:8000/health
```

### Option B: Fully containerized (app + migrations also in Docker)

```bash
docker compose up --build
```

Builds the app image, runs migrations, then starts the app in a container —
no local Python install needed at all. **Don't run this at the same time as
Option A** — both bind to host port 8000, so pick one or the other for
serving traffic; the shared `db` service can stay up either way.

To stop and remove containers (keeping volumes/data): `docker compose down`.
To also wipe all data: `docker compose down -v`.

`POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `UVICORN_WORKERS` in
`.env` only affect the Compose stack (they configure the containerized
Postgres and the app's worker count) — they're not read by a local
`uvicorn app.main:app` run.

**Note:** if you have a native Postgres (e.g. Postgres.app) also listening
on port 5432, stop it first — only one process can bind that port on the
host.

## Tests

```bash
pytest              # fast, mocked AI calls, isolated test database
pytest -m live      # opt-in: real OpenAI calls, validates response shape
python scripts/evaluate_accuracy.py   # accuracy evaluation against real API
```
