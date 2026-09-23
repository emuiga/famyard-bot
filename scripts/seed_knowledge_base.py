import csv
from pathlib import Path

from app.db.supabase import get_supabase

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


def main() -> None:
    rows = load_rows()
    get_supabase().table("knowledge_base").upsert(rows).execute()
    print(f"Seeded {len(rows)} rows into knowledge_base")


if __name__ == "__main__":
    main()
