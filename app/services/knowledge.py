import asyncio

from app.core.config import get_settings
from app.db.supabase import get_supabase
from app.services.embeddings import embed_query


async def search(query: str) -> list[dict]:
    """Return knowledge chunks most similar to the query."""
    settings = get_settings()
    embedding = await embed_query(query)
    # supabase-py is sync; keep it off the event loop
    resp = await asyncio.to_thread(
        lambda: get_supabase()
        .rpc(
            "match_knowledge_chunks",
            {
                "query_embedding": embedding,
                "match_count": settings.match_count,
                "match_threshold": settings.match_threshold,
            },
        )
        .execute()
    )
    return resp.data or []


def format_context(matches: list[dict]) -> str:
    blocks = []
    for m in matches:
        block = f"[{m['kb_id']}] {m['title']}\n{m['content']}"
        if m.get("source_url"):
            block += f"\nLink: {m['source_url']}"
        if m.get("needs_verification"):
            block += f"\n(Unverified: {m['needs_verification']})"
        blocks.append(block)
    return "\n\n---\n\n".join(blocks)
