import asyncio
import logging

from postgrest.exceptions import APIError

from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

_UNIQUE_VIOLATION = "23505"


async def claim(message_id: str) -> bool:
    """Record a WhatsApp message id. Returns False if it was already handled."""
    try:
        await asyncio.to_thread(
            lambda: get_supabase().table("processed_messages").insert({"message_id": message_id}).execute()
        )
    except APIError as e:
        if e.code == _UNIQUE_VIOLATION:
            return False
        logger.exception("Failed to record message %s", message_id)
    except Exception:
        # Prefer a possible duplicate reply over no reply
        logger.exception("Failed to record message %s", message_id)
    return True
