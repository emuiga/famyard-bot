import asyncio
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.services import assistant, dedupe, memory, whatsapp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

MAX_MESSAGE_LENGTH = 2000
# Wait for the phone-number copy of a message before flagging a username-only copy
PHONE_COPY_WAIT_SECONDS = 10

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
                if "id" not in message:
                    continue
                sender = _sender(message, value)
                if not sender:
                    # Never fail the request: Meta would keep retrying the whole batch
                    background_tasks.add_task(handle_without_phone, message["id"], message.get("type"))
                    continue
                # Reply after returning 200 so Meta doesn't retry and cause duplicate replies
                if message.get("type") == "text":
                    background_tasks.add_task(
                        handle_message, message["id"], sender, message.get("text", {}).get("body", "")
                    )
                elif message.get("type") in UNSUPPORTED_TYPES:
                    background_tasks.add_task(handle_unsupported, message["id"], sender)
    return {"status": "received"}


def _sender(message: dict, value: dict) -> str | None:
    """WhatsApp id to reply to: the message's `from`, else the matching contact's `wa_id`."""
    if message.get("from"):
        return message["from"]
    contacts = value.get("contacts") or []
    return contacts[0].get("wa_id") if len(contacts) == 1 else None


async def handle_message(message_id: str, sender: str, text: str) -> None:
    if not await dedupe.claim(message_id):
        logger.info("Skipping duplicate message %s", message_id)
        return
    logger.info("Message from %s: %s", sender, text)
    if len(text) > MAX_MESSAGE_LENGTH:
        await _send(sender, "Your message is a bit long. Please send a shorter question.")
        return

    try:
        history = await memory.get_history(sender)
    except Exception:
        logger.exception("Failed to load history for %s", sender)
        history = []

    reply = await assistant.answer(text, history)
    await _send(sender, reply)

    try:
        await memory.save_messages(
            sender,
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
        )
    except Exception:
        logger.exception("Failed to save history for %s", sender)


async def handle_without_phone(message_id: str, message_type: str | None) -> None:
    """Meta may also deliver a copy keyed only by a username-style user id (from_user_id).

    Don't claim the id: the copy with the phone number may arrive after this one.
    """
    await asyncio.sleep(PHONE_COPY_WAIT_SECONDS)
    try:
        handled = await dedupe.is_processed(message_id)
    except Exception:
        logger.exception("Failed to check message %s", message_id)
        return
    if handled:
        logger.info("Skipping copy of message %s without phone number", message_id)
    else:
        logger.warning("Unanswered %s message %s: sender has no phone number", message_type, message_id)


async def handle_unsupported(message_id: str, sender: str) -> None:
    if await dedupe.claim(message_id):
        await _send(sender, UNSUPPORTED_REPLY)


async def _send(to: str, body: str) -> None:
    try:
        await whatsapp.send_text(to, body)
    except Exception:
        logger.exception("Failed to send reply to %s", to)
