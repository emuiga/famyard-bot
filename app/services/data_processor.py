from app.core.config import get_settings
from app.utils.chunking import count_tokens, split_text


def build_document(row: dict) -> str:
    """Turn a knowledge base row into labelled text for embedding.

    Sample questions are included so user phrasing matches closely.
    """
    category = " / ".join(filter(None, [row.get("category"), row.get("subcategory")]))
    fields = [
        ("Title", row.get("title")),
        ("Category", category),
        ("Location", ", ".join(filter(None, [row.get("location"), row.get("county")]))),
        ("Property type", row.get("property_type")),
        ("Plot size", row.get("plot_size")),
        ("Price", row.get("price")),
        ("Status", row.get("status")),
        ("Content", row.get("content")),
        ("Common questions", " | ".join(row.get("sample_questions") or [])),
        ("Keywords", ", ".join(row.get("keywords") or [])),
    ]
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


def build_chunks(row: dict) -> list[dict]:
    """Split a row's document into chunks ready for embedding and insertion."""
    settings = get_settings()
    pieces = split_text(
        build_document(row),
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    # Prefix later chunks with the title so each chunk stands on its own
    title = row.get("title") or ""
    return [
        {
            "kb_id": row["id"],
            "chunk_index": i,
            "content": text if i == 0 or not title else f"Title: {title}\n{text}",
            "token_count": count_tokens(text),
        }
        for i, text in enumerate(pieces)
    ]
