import re


def to_whatsapp(text: str) -> str:
    """Convert common Markdown the model may emit into WhatsApp formatting."""
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)  # **bold** -> *bold*
    text = re.sub(r"__(.+?)__", r"_\1_", text)  # __italic__ -> _italic_
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)  # headings -> bold
    return text
