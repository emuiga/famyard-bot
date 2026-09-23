from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings

_BATCH_SIZE = 100


@lru_cache
def _client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


async def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    settings = get_settings()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        resp = await _client().aio.models.embed_content(
            model=settings.embedding_model,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimensions,
            ),
        )
        if len(resp.embeddings) != len(batch):
            raise ValueError(f"Expected {len(batch)} embeddings, got {len(resp.embeddings)}")
        vectors.extend(e.values for e in resp.embeddings)
    return vectors


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed knowledge base content for storage."""
    return await _embed(texts, "RETRIEVAL_DOCUMENT")


async def embed_query(text: str) -> list[float]:
    """Embed a customer question for search."""
    return (await _embed([text], "RETRIEVAL_QUERY"))[0]
