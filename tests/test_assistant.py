import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import assistant, knowledge


def test_search_query_includes_recent_customer_messages():
    history = [
        {"role": "user", "content": "Tell me about Nanyuki"},
        {"role": "assistant", "content": "Nanyuki Townview..."},
        {"role": "user", "content": "How big are the plots?"},
        {"role": "assistant", "content": "50 x 100 ft"},
    ]
    query = assistant._search_query("Does it have water?", history)
    assert query == "Tell me about Nanyuki\nHow big are the plots?\nDoes it have water?"


def _fake_client(text="Hello *there*", stop_reason="end_turn"):
    response = SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=response)
    return client


def test_answer_sends_history_and_drops_leading_assistant_messages():
    client = _fake_client()
    history = [
        {"role": "assistant", "content": "orphan"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    with patch.object(assistant, "_client", return_value=client), patch.object(
        knowledge, "search", AsyncMock(return_value=[])
    ):
        reply = asyncio.run(assistant.answer("Where are you?", history))

    messages = client.messages.create.call_args.kwargs["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert "Where are you?" in messages[-1]["content"]
    assert reply == "Hello *there*"


def test_answer_converts_markdown():
    with patch.object(assistant, "_client", return_value=_fake_client("**Yes**")), patch.object(
        knowledge, "search", AsyncMock(return_value=[])
    ):
        assert asyncio.run(assistant.answer("Water?")) == "*Yes*"


def test_answer_falls_back_on_error():
    with patch.object(knowledge, "search", AsyncMock(side_effect=RuntimeError("down"))):
        assert asyncio.run(assistant.answer("Hi")) == assistant.FALLBACK_REPLY


def test_answer_falls_back_on_refusal():
    with patch.object(assistant, "_client", return_value=_fake_client(stop_reason="refusal")), patch.object(
        knowledge, "search", AsyncMock(return_value=[])
    ):
        assert asyncio.run(assistant.answer("Hi")) == assistant.FALLBACK_REPLY


def test_format_context_marks_unverified():
    context = knowledge.format_context(
        [{"kb_id": "FY-002", "title": "Stats", "content": "1,200+ sales", "needs_verification": "conflicting"}]
    )
    assert "(Unverified: conflicting)" in context


def test_format_context_includes_links_when_present():
    context = knowledge.format_context([
        {"kb_id": "FY-062", "title": "Nanyuki", "content": "Plots", "source_url": "https://famyard.co.ke/nanyuki/"},
        {"kb_id": "FY-001", "title": "About", "content": "Company"},
    ])
    assert "Link: https://famyard.co.ke/nanyuki/" in context
    assert context.count("Link:") == 1
