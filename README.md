# AI Customer Feedback Intelligence Platform

AI-powered customer feedback intelligence system (FastAPI, OpenAI, RAG,
PostgreSQL, ChromaDB). See `AI_Customer_Feedback_Intelligence_Architecture.md`
in the repo root for the full architecture.

## Phase 1: Project Initialization

This phase sets up the project skeleton, virtual environment, and a minimal
FastAPI app with a health check endpoint. No database or AI logic yet.

## Setup

```bash
cd feedback-intelligence-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

## Verify

```bash
curl http://127.0.0.1:8000/health
```
