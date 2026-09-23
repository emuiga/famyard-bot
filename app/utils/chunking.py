import re
from functools import lru_cache

import tiktoken

# Separators tried in order: paragraphs, lines, sentences, words.
_SEPARATORS = [r"\n\s*\n", r"\n", r"(?<=[.!?])\s+", r"\s+"]


@lru_cache
def _encoding() -> tiktoken.Encoding:
    # cl100k_base approximates token counts for any embedding model
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding().encode(text))


def _split(text: str, max_tokens: int, level: int = 0) -> list[str]:
    """Split text into pieces that each fit within max_tokens, preferring natural boundaries."""
    if count_tokens(text) <= max_tokens:
        return [text]
    if level == len(_SEPARATORS):
        tokens = _encoding().encode(text)
        return [_encoding().decode(tokens[i : i + max_tokens]) for i in range(0, len(tokens), max_tokens)]

    pieces = []
    for part in re.split(_SEPARATORS[level], text):
        if part.strip():
            pieces.extend(_split(part.strip(), max_tokens, level + 1))
    return pieces


def split_text(text: str, max_tokens: int = 400, overlap_tokens: int = 50) -> list[str]:
    """Split text into chunks of at most max_tokens, carrying overlap_tokens of context between chunks.

    Text that already fits is returned as a single chunk.
    """
    text = text.strip()
    if not text:
        return []
    if count_tokens(text) <= max_tokens:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    for piece in _split(text, max_tokens - overlap_tokens):
        if current and count_tokens(" ".join([*current, piece])) > max_tokens:
            chunks.append(" ".join(current))
            # Keep trailing pieces from the previous chunk as overlap
            overlap: list[str] = []
            for prev in reversed(current):
                if count_tokens(" ".join([prev, *overlap])) > overlap_tokens:
                    break
                overlap.insert(0, prev)
            current = overlap
        current.append(piece)
    if current:
        chunks.append(" ".join(current))
    return chunks
