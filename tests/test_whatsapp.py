import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import whatsapp


def _sent_payloads(to: str, body: str) -> list[dict]:
    response = MagicMock(is_error=False)
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    with patch.object(whatsapp.httpx, "AsyncClient", return_value=client):
        asyncio.run(whatsapp.send_text(to, body))
    return [c.kwargs["json"] for c in client.post.await_args_list]


def test_phone_number_is_sent_in_to():
    [payload] = _sent_payloads("254700000000", "hi")
    assert payload["to"] == "254700000000" and "recipient" not in payload


def test_user_id_is_sent_in_recipient():
    [payload] = _sent_payloads("KE.3659347954227944", "hi")
    assert payload["recipient"] == "KE.3659347954227944" and "to" not in payload


def test_long_reply_is_sent_in_parts():
    payloads = _sent_payloads("254700000000", "word " * 2000)
    assert len(payloads) == 3
