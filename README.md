# Famyard Bot

WhatsApp bot for Famyard Enterprises, built with FastAPI and Supabase.
Answers customer questions from a knowledge base using Gemini embeddings for search and an Anthropic model for replies,
with per-number conversation memory.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # fill in values
```

Run the files in `supabase/migrations/` in order in the Supabase SQL editor.

## Seed knowledge base

```bash
python -m scripts.seed_knowledge_base
```

Re-run after editing `data/famyard_knowledge_base.csv` to refresh rows and embeddings.

## Run

```bash
uvicorn app.main:app --reload
```

The webhook is served at `/webhook`. In the Meta App Dashboard, set the callback URL to
`https://<your-host>/webhook`, the verify token to `WHATSAPP_VERIFY_TOKEN`, and subscribe to `messages`.
Set `WHATSAPP_APP_SECRET` (App settings > Basic) so incoming requests are verified; without it,
unsigned requests are only accepted when `APP_ENV=development`.

## Test

```bash
pytest
```
