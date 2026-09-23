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
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") != "text":
                    continue
                # Reply after returning 200 so Meta doesn't retry and cause duplicate replies
                background_tasks.add_task(
                    handle_message, message["id"], message["from"], message["text"]["body"]
                )
    return {"status": "received"}


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


async def _send(to: str, body: str) -> None:
    try:
        await whatsapp.send_text(to, body)
    except Exception:
        logger.exception("Failed to send reply to %s", to)
