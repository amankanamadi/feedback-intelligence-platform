# AI Customer Feedback Intelligence Platform

AI-powered customer feedback intelligence system (FastAPI, OpenAI, RAG,
PostgreSQL, ChromaDB). See `AI_Customer_Feedback_Intelligence_Architecture.md`
in the repo root for the full architecture.

## Option A: Local development (venv + local Postgres)

```bash
cd feedback-intelligence-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY and DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/dashboard, or verify the API directly:

```bash
curl http://127.0.0.1:8000/health
```

## Option B: Docker Compose

Builds the app image, starts Postgres, runs migrations, then starts the app —
no local Python/Postgres install needed at all.

```bash
cd feedback-intelligence-platform
cp .env.example .env   # then fill in OPENAI_API_KEY at minimum
docker compose up --build
```

Open http://127.0.0.1:8000/dashboard once it's up. ChromaDB runs embedded in
the app container; its data persists in the `chroma_data` Docker volume, and
Postgres data persists in `postgres_data`. To stop and remove containers
(keeping volumes/data): `docker compose down`. To also wipe all data:
`docker compose down -v`.

`POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `UVICORN_WORKERS` in
`.env` only affect the Compose stack (they configure the containerized
Postgres and the app's worker count) — they're not read by a local
`uvicorn app.main:app` run.

## Tests

```bash
pytest              # fast, mocked AI calls, isolated test database
pytest -m live      # opt-in: real OpenAI calls, validates response shape
python scripts/evaluate_accuracy.py   # accuracy evaluation against real API
```
