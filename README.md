# Famyard Bot

WhatsApp bot for Famyard Enterprises, built with FastAPI and Supabase.

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

Run `supabase/migrations/001_knowledge_base.sql` in the Supabase SQL editor, then:

```bash
python -m scripts.seed_knowledge_base
```
