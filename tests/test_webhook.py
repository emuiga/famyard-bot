import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes import webhook
from app.main import app

client = TestClient(app)


def _post(payload: dict, secret: str = "test-secret", signature: str | None = None):
    body = json.dumps(payload).encode()
    if signature is None:
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signature})


def _payload(*messages: dict) -> dict:
    return {"entry": [{"changes": [{"value": {"messages": list(messages)}}]}]}


def _text(body: str, msg_id: str = "wamid.1", sender: str = "254700000000") -> dict:
    return {"id": msg_id, "from": sender, "type": "text", "text": {"body": body}}


@pytest.fixture
def services():
    """Mock every external dependency of the webhook."""
    with (
        patch.object(webhook.dedupe, "claim", AsyncMock(return_value=True)) as claim,
        patch.object(webhook.memory, "get_history", AsyncMock(return_value=[])) as get_history,
        patch.object(webhook.memory, "save_messages", AsyncMock()) as save_messages,
        patch.object(webhook.assistant, "answer", AsyncMock(return_value="Reply")) as answer,
        patch.object(webhook.whatsapp, "send_text", AsyncMock()) as send_text,
    ):
        yield {
            "claim": claim,
            "get_history": get_history,
            "save_messages": save_messages,
            "answer": answer,
            "send_text": send_text,
        }


def test_verify_returns_challenge():
    params = {"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"}
    resp = client.get("/webhook", params=params)
    assert resp.status_code == 200 and resp.text == "42"


def test_verify_rejects_wrong_token():
    params = {"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "42"}
    assert client.get("/webhook", params=params).status_code == 403


def test_rejects_bad_signature(services):
    assert _post(_payload(_text("hi")), signature="sha256=00").status_code == 401
    services["answer"].assert_not_called()


def test_rejects_missing_secret_outside_development(settings, services):
    settings.whatsapp_app_secret = ""
    assert _post(_payload(_text("hi")), signature="").status_code == 401


def test_text_message_is_answered_and_saved(services):
    services["get_history"].return_value = [{"role": "user", "content": "earlier"}]
    assert _post(_payload(_text("Where are you?"))).status_code == 200

    services["answer"].assert_awaited_once_with("Where are you?", [{"role": "user", "content": "earlier"}])
    services["send_text"].assert_awaited_once_with("254700000000", "Reply")
    services["save_messages"].assert_awaited_once_with(
        "254700000000",
        [{"role": "user", "content": "Where are you?"}, {"role": "assistant", "content": "Reply"}],
    )


def test_duplicate_message_is_skipped(services):
    services["claim"].return_value = False
    _post(_payload(_text("hi")))
    services["answer"].assert_not_called()
    services["send_text"].assert_not_called()


def test_long_message_gets_short_reply_without_llm(services):
    _post(_payload(_text("x" * 2001)))
    services["answer"].assert_not_called()
    assert "shorter" in services["send_text"].call_args.args[1]


def test_media_message_gets_text_only_reply(services):
    _post(_payload({"id": "wamid.2", "from": "254700000000", "type": "image", "image": {}}))
    services["answer"].assert_not_called()
    services["send_text"].assert_awaited_once_with("254700000000", webhook.UNSUPPORTED_REPLY)


def test_reaction_is_ignored(services):
    _post(_payload({"id": "wamid.3", "from": "254700000000", "type": "reaction", "reaction": {}}))
    services["send_text"].assert_not_called()


def test_status_updates_are_ignored(services):
    assert _post({"entry": [{"changes": [{"value": {"statuses": [{"status": "read"}]}}]}]}).status_code == 200
    services["send_text"].assert_not_called()


def test_reply_still_sent_when_history_fails(services):
    services["get_history"].side_effect = RuntimeError("db down")
    _post(_payload(_text("hi")))
    services["answer"].assert_awaited_once_with("hi", [])
    services["send_text"].assert_awaited_once()


def test_sender_falls_back_to_contact_wa_id(services):
    payload = {"entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": "254711111111", "profile": {"name": "A"}}],
        "messages": [{"id": "wamid.4", "type": "text", "text": {"body": "hi"}}],
    }}]}]}
    _post(payload)
    services["send_text"].assert_awaited_once_with("254711111111", "Reply")


def test_message_with_only_user_id_is_not_answered_or_errored(services):
    payload = {"entry": [{"changes": [{"value": {
        "contacts": [{"user_id": "KE.123", "profile": {"name": "A"}}],
        "messages": [{"id": "wamid.5", "from_user_id": "KE.123", "type": "text", "text": {"body": "hi"}}],
    }}]}]}
    with (
        patch.object(webhook, "PHONE_COPY_WAIT_SECONDS", 0),
        patch.object(webhook.dedupe, "is_processed", AsyncMock(return_value=True)) as is_processed,
    ):
        assert _post(payload).status_code == 200
    is_processed.assert_awaited_once_with("wamid.5")
    services["claim"].assert_not_called()
    services["answer"].assert_not_called()
    services["send_text"].assert_not_called()
