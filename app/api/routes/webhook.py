import hashlib
import hmac
import json
import logging
from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.services import assistant, dedupe, memory, whatsapp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

MAX_MESSAGE_LENGTH = 2000
# Media we can't read yet; reactions and system events are ignored silently
UNSUPPORTED_TYPES = {"image", "audio", "video", "document", "sticker", "location", "contacts"}
UNSUPPORTED_REPLY = (
    "Sorry, I can only read text messages for now. Please type your question, "
    "or call +254 119 222666 to speak with the Famyard team."
)


@router.get("", response_class=PlainTextResponse)
def verify(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> str:
    if mode == "subscribe" and token == get_settings().whatsapp_verify_token:
        return challenge
    raise HTTPException(status_code=403, detail="Verification failed")


def _valid_signature(body: bytes, header: str | None) -> bool:
    settings = get_settings()
    if not settings.whatsapp_app_secret:
        # Allow unsigned requests only for local development
        return settings.app_env == "development"
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@router.post("")
async def receive(request: Request, background_tasks: BackgroundTasks) -> dict:
    body = await request.body()
    if not _valid_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="Invalid signature")
    data = json.loads(body)
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                sender = _sender(message, value)
                if not sender:
                    # Never fail the request: Meta would keep retrying the whole batch
                    logger.warning("Skipping message without sender: keys=%s", sorted(message))
                    continue
                key = _dedupe_key(message, sender)
                # Reply after returning 200 so Meta doesn't retry and cause duplicate replies
                if message.get("type") == "text":
                    background_tasks.add_task(
                        handle_message, key, sender, message.get("text", {}).get("body", "")
                    )
                elif message.get("type") in UNSUPPORTED_TYPES:
                    background_tasks.add_task(handle_unsupported, key, sender)
    return {"status": "received"}


@dataclass(frozen=True)
class Sender:
    reply_to: str  # phone number when Meta provides one, else the business-scoped user id
    user_key: str  # stable id for conversation history: the business-scoped user id when present


def _sender(message: dict, value: dict) -> Sender | None:
    contacts = value.get("contacts") or []
    contact = contacts[0] if len(contacts) == 1 else {}
    phone = message.get("from") or contact.get("wa_id")
    # Business-scoped user id: always sent, even when the phone number is withheld
    user_id = message.get("from_user_id") or contact.get("user_id")
    if not (phone or user_id):
        return None
    return Sender(reply_to=phone or user_id, user_key=user_id or phone)


def _dedupe_key(message: dict, sender: Sender) -> str:
    """Meta can deliver one message twice with different ids (with and without the phone number),
    so identify it by sender, timestamp and content instead."""
    if not message.get("timestamp"):
        return message.get("id", "")
    content = json.dumps(message.get(message.get("type", ""), {}), sort_keys=True)
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"{sender.user_key}:{message['timestamp']}:{digest}"


async def handle_message(key: str, sender: Sender, text: str) -> None:
    if not await dedupe.claim(key):
        logger.info("Skipping duplicate message %s", key)
        return
    logger.info("Message from %s: %s", sender.reply_to, text)
    if len(text) > MAX_MESSAGE_LENGTH:
        await _send(sender, "Your message is a bit long. Please send a shorter question.")
        return

    try:
        history = await memory.get_history(sender.user_key)
    except Exception:
        logger.exception("Failed to load history for %s", sender.user_key)
        history = []

    reply = await assistant.answer(text, history)
    await _send(sender, reply)

    try:
        await memory.save_messages(
            sender.user_key,
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
        )
    except Exception:
        logger.exception("Failed to save history for %s", sender.user_key)


async def handle_unsupported(key: str, sender: Sender) -> None:
    if await dedupe.claim(key):
        await _send(sender, UNSUPPORTED_REPLY)


async def _send(sender: Sender, body: str) -> None:
    try:
        await whatsapp.send_text(sender.reply_to, body)
    except Exception:
        logger.exception("Failed to send reply to %s", sender.reply_to)
