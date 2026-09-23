from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings

# OpenAI accepts up to 2048 inputs per request; stay well under.
_BATCH_SIZE = 100


@lru_cache
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        resp = await _client().embeddings.create(
            model=settings.embedding_model,
            input=texts[i : i + _BATCH_SIZE],
            dimensions=settings.embedding_dimensions,
        )
        vectors.extend(item.embedding for item in sorted(resp.data, key=lambda d: d.index))
    return vectors


async def embed_text(text: str) -> list[float]:
    return (await embed_batch([text]))[0]
