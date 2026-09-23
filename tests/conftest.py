import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def settings():
    """Fresh settings per test with a known app secret; nothing here calls real services."""
    get_settings.cache_clear()
    s = get_settings()
    s.app_env = "test"
    s.whatsapp_app_secret = "test-secret"
    s.whatsapp_verify_token = "verify-me"
    yield s
    get_settings.cache_clear()
