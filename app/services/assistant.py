import logging
from functools import lru_cache

import anthropic

from app.core.config import get_settings
from app.services import knowledge
from app.utils.formatting import to_whatsapp

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the WhatsApp assistant for Famyard Enterprises Ltd, a real estate company in Nyeri, Kenya that sells value-added plots in Nyeri County, Laikipia County and Nanyuki.

Answer using only the information in <knowledge>. If it doesn't cover the question, say you're not sure and share Famyard's contacts instead of guessing.

Hand over to the Famyard team for anything needing live information: exact prices, current plot availability, specific plot numbers, deposit or instalment terms, booking a site visit, payment confirmation, or an existing client's title deed status. Contacts: call +254 119 222666, WhatsApp +254 721 383 090, email contact@famyard.co.ke.

If a fact is marked Unverified, don't state it as certain.

Style: friendly, short replies suited to WhatsApp (a few sentences, short lists where helpful). Use *bold* for emphasis, never Markdown headings or tables. Reply in the language the customer writes in."""

FALLBACK_REPLY = (
    "Sorry, I'm having trouble right now. Please call +254 119 222666 "
    "or WhatsApp +254 721 383 090 and the Famyard team will help you."
)


@lru_cache
def _client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)


async def answer(question: str) -> str:
    settings = get_settings()
    try:
        matches = await knowledge.search(question)
        response = await _client().messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"<knowledge>\n{knowledge.format_context(matches)}\n</knowledge>\n\n"
                    f"Customer message: {question}",
                }
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
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return to_whatsapp(text) if text else FALLBACK_REPLY
