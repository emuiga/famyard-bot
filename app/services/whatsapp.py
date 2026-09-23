import httpx

from app.core.config import get_settings
from app.utils.formatting import split_message


async def send_text(to: str, body: str) -> None:
    """Send a text message, split into several if it exceeds WhatsApp's length limit."""
    settings = get_settings()
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}"
        f"/{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        for part in split_message(body):
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": part},
            }
            resp = await client.post(url, json=payload, headers=headers)
            if resp.is_error:
                # Meta explains the failure in the body (e.g. recipient not allowed, token expired)
                raise RuntimeError(f"WhatsApp send failed ({resp.status_code}): {resp.text}")
