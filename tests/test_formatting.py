from app.utils.formatting import split_message, to_whatsapp


def test_markdown_bold_becomes_whatsapp_bold():
    assert to_whatsapp("Kuhusu **ndiyo** sawa") == "Kuhusu *ndiyo* sawa"


def test_headings_become_bold():
    assert to_whatsapp("## Offices\nNyeri") == "*Offices*\nNyeri"


def test_whatsapp_formatting_is_untouched():
    assert to_whatsapp("*bold* and _italic_") == "*bold* and _italic_"


def test_short_message_is_not_split():
    assert split_message("hello") == ["hello"]


def test_long_message_splits_within_limit_without_losing_text():
    text = ("para " * 1000) + "\n\n" + ("line " * 1000)
    parts = split_message(text, limit=4096)
    assert len(parts) > 1
    assert all(len(p) <= 4096 for p in parts)
    assert "".join(parts).replace(" ", "").replace("\n", "") == text.replace(" ", "").replace("\n", "")
