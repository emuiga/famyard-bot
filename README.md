# Famyard Bot

WhatsApp bot for Famyard Enterprises, built with FastAPI and Supabase.
Answers customer questions from a knowledge base using OpenAI embeddings for search and an Anthropic model for replies.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
```

## Run

```bash
uvicorn app.main:app --reload
```

## Seed knowledge base

Run the files in `supabase/migrations/` in order in the Supabase SQL editor, then:

```bash
python -m scripts.seed_knowledge_base
```

Re-run the seed after editing `data/famyard_knowledge_base.csv` to refresh rows and embeddings.
