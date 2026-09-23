import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.services import whatsapp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("", response_class=PlainTextResponse)
def verify(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> str:
    if mode == "subscribe" and token == get_settings().whatsapp_verify_token:
        return challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive(request: Request) -> dict:
    data = await request.json()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = message["from"]
                text = message["text"]["body"]
                logger.info("Message from %s: %s", sender, text)
                # TODO: replace echo with knowledge base lookup
                await whatsapp.send_text(sender, f"You said: {text}")
    return {"status": "received"}
