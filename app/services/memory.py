import asyncio
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.db.supabase import get_supabase

TABLE = "conversation_messages"


async def get_history(phone: str) -> list[dict]:
    """Return recent messages for a phone number, oldest first, as {role, content} dicts."""
    settings = get_settings()
    since = datetime.now(UTC) - timedelta(hours=settings.history_window_hours)
    resp = await asyncio.to_thread(
        lambda: get_supabase()
        .table(TABLE)
        .select("role, content")
        .eq("phone", phone)
        .gte("created_at", since.isoformat())
        .order("created_at", desc=True)
        .order("id", desc=True)
        .limit(settings.history_max_messages)
        .execute()
    )
    return list(reversed(resp.data or []))


async def save_messages(phone: str, messages: list[dict]) -> None:
    """Store messages ({role, content}) for a phone number, in order."""
    rows = [{"phone": phone, **m} for m in messages]
    await asyncio.to_thread(lambda: get_supabase().table(TABLE).insert(rows).execute())
