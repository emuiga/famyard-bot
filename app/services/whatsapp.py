import httpx

from app.core.config import get_settings


async def send_text(to: str, body: str) -> dict:
    settings = get_settings()
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}"
        f"/{settings.whatsapp_phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()
