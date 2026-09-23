import re


def to_whatsapp(text: str) -> str:
    """Convert common Markdown the model may emit into WhatsApp formatting."""
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)  # **bold** -> *bold*
    text = re.sub(r"__(.+?)__", r"_\1_", text)  # __italic__ -> _italic_
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)  # headings -> bold
    return text


def split_message(text: str, limit: int = 4096) -> list[str]:
    """Split text into WhatsApp-sized parts, breaking at paragraphs, then lines, then spaces."""
    parts = []
    while len(text) > limit:
        window = text[:limit]
        cut = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(" "))
        if cut <= 0:
            cut = limit
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts
