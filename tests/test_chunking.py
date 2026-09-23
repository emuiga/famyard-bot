from app.utils.chunking import count_tokens, split_text


def test_short_text_is_one_chunk():
    assert split_text("Plots in Nyeri with water.") == ["Plots in Nyeri with water."]


def test_empty_text_has_no_chunks():
    assert split_text("   ") == []


def test_chunks_respect_max_tokens():
    text = "\n\n".join(f"Paragraph {i}. " + "Famyard sells serviced plots in Nyeri. " * 20 for i in range(10))
    chunks = split_text(text, max_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    assert all(count_tokens(c) <= 100 for c in chunks)


def test_unbroken_text_falls_back_to_token_split():
    chunks = split_text("x" * 5000, max_tokens=100, overlap_tokens=10)
    assert all(count_tokens(c) <= 100 for c in chunks)


def test_chunks_overlap():
    sentences = " ".join(f"Sentence number {i} is here." for i in range(60))
    chunks = split_text(sentences, max_tokens=60, overlap_tokens=15)
    assert chunks[1].split(".")[0] in chunks[0]
