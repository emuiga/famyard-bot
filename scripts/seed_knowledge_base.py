import asyncio
import csv
from pathlib import Path

from app.core.config import get_settings
from app.db.supabase import get_supabase
from app.services.data_processor import build_chunks
from app.services.embeddings import embed_batch

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "famyard_knowledge_base.csv"


def _split(value: str, sep: str) -> list[str]:
    return [v.strip() for v in value.split(sep) if v.strip()]


def load_rows() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            row = {k: (v or None) for k, v in row.items()}
            row["sample_questions"] = _split(row["sample_questions"] or "", "|")
            row["keywords"] = _split(row["keywords"] or "", ",")
            rows.append(row)
        return rows


async def main() -> None:
    sb = get_supabase()
    rows = load_rows()
    sb.table("knowledge_base").upsert(rows).execute()
    print(f"Upserted {len(rows)} rows into knowledge_base")

    chunks = [chunk for row in rows for chunk in build_chunks(row)]
    vectors = await embed_batch([c["content"] for c in chunks])
    dims = get_settings().embedding_dimensions
    for chunk, vector in zip(chunks, vectors, strict=True):
        if len(vector) != dims:
            raise ValueError(f"Expected {dims} dimensions, got {len(vector)}")
        chunk["embedding"] = vector

    # Replace chunks so edited or shortened rows don't leave stale pieces behind
    ids = [row["id"] for row in rows]
    sb.table("knowledge_chunks").delete().in_("kb_id", ids).execute()
    sb.table("knowledge_chunks").insert(chunks).execute()
    print(f"Embedded {len(chunks)} chunks into knowledge_chunks")


if __name__ == "__main__":
    asyncio.run(main())
