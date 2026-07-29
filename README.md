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

`.env`'s `JWT_SECRET_KEY` can stay empty for local dev (`DEBUG=true`
allows it), but is **required** — the app refuses to start without it —
once `DEBUG=false`, which is exactly what the `app` service in Option B
below sets. Generate one with `openssl rand -hex 32` before using Option B.

### Option A: Local dev (venv + shared Docker database)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Verify the API directly, or open http://127.0.0.1:8000/docs for interactive API docs:

```bash
curl http://127.0.0.1:8000/health
```

The product frontend is the Next.js app in `web/` (see `web/README.md`) -
it's a separate app on its own origin, not served by this backend.

### Creating an admin account

Every account created via signup/`POST /auth/register` gets the `user`
role — there's no self-service or scripted way to become an admin (a
deliberate, currently-unaddressed gap, not an oversight). To get the
first admin: register a normal account through the app, then promote it
directly in the database:

```bash
docker exec -it feedback-intelligence-platform-db-1 psql -U feedback_app -d feedback_intelligence \
  -c "UPDATE users SET role = 'ADMIN' WHERE email = 'you@example.com';"
```

(Adjust the container name if it differs - check with `docker compose ps`.
Log out and back in afterward so a fresh JWT picks up the new role.)

### Option B: Fully containerized (backend + frontend + migrations, one command)

```bash
docker compose up --build
```

Builds and starts everything: the database, a one-shot migration
container, the FastAPI backend on `:8000`, and the Next.js frontend on
`:3000` — no local Python or Node install needed at all. Open
http://localhost:3000/login once it's up.

This is a production-style build of the frontend (no hot-reload) - for
day-to-day frontend iteration, run `npm run dev` in `web/` against a
`docker compose up -d db app`-only stack instead (Option A below covers
the backend half of that).

**Don't run Option A's `uvicorn --reload` at the same time as this** —
both bind to host port 8000, so pick one or the other for serving
backend traffic; the shared `db` service can stay up either way.

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
