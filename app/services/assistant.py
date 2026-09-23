import logging
from functools import lru_cache

import anthropic

from app.core.config import get_settings
from app.services import knowledge
from app.utils.formatting import to_whatsapp

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the WhatsApp assistant for Famyard Enterprises Ltd, a real estate company in Nyeri, Kenya that sells value-added plots in Nyeri County, Laikipia County and Nanyuki.

Answer using only the information in <knowledge>. Don't add examples, figures or details that aren't there, even if they seem likely. If it doesn't cover the question, say you're not sure and share Famyard's contacts instead of guessing.

Hand over to the Famyard team for anything needing live information: exact prices, current plot availability, specific plot numbers, deposit or instalment terms, booking a site visit, payment confirmation, or an existing client's title deed status. Contacts: call +254 119 222666, WhatsApp +254 721 383 090, email contact@famyard.co.ke. Share these contacts when handing over or when asked, not in every reply; if you've already shared them in this conversation, just say the team can help.

If a fact is marked Unverified, don't state it as certain.

Only say a specific estate has a feature (water, electricity, title deeds, roads, etc.) if that estate's own entry says so. General company statements don't confirm details for a particular estate; if it's not stated, say it isn't confirmed and suggest checking with the team.

Style: friendly, short replies suited to WhatsApp (a few sentences, short lists where helpful). Use *bold* for emphasis, never Markdown headings or tables. Reply in the language the customer writes in."""

FALLBACK_REPLY = (
    "Sorry, I'm having trouble right now. Please call +254 119 222666 "
    "or WhatsApp +254 721 383 090 and the Famyard team will help you."
)


@lru_cache
def _client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def _search_query(question: str, history: list[dict]) -> str:
    """Include recent customer messages so follow-ups like "how much is it?" find the right entries."""
    previous = [m["content"] for m in history if m["role"] == "user"][-2:]
    return "\n".join([*previous, question])


async def answer(question: str, history: list[dict] | None = None) -> str:
    """Reply to a customer message. history is prior {role, content} messages, oldest first."""
    settings = get_settings()
    history = list(history or [])
    # Conversation must start with a customer message
    while history and history[0]["role"] != "user":
        history.pop(0)
    try:
        matches = await knowledge.search(_search_query(question, history))
        response = await _client().messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                *({"role": m["role"], "content": m["content"]} for m in history),
                {
                    "role": "user",
                    "content": f"<knowledge>\n{knowledge.format_context(matches)}\n</knowledge>\n\n"
                    f"Customer message: {question}",
                },
            ],
        )
    except anthropic.APIStatusError as e:
        logger.error("LLM API error %s (request %s): %s", e.status_code, e.request_id, e.message)
        return FALLBACK_REPLY
    except Exception:
        logger.exception("Failed to answer message")
        return FALLBACK_REPLY

    if response.stop_reason == "refusal":
        return FALLBACK_REPLY
    if response.stop_reason == "max_tokens":
        logger.warning("Reply hit max_tokens (%s) and may be cut off", settings.llm_max_tokens)
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return to_whatsapp(text) if text else FALLBACK_REPLY
