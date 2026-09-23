from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    supabase_url: str = ""
    supabase_key: str = ""

    gemini_api_key: str = ""
    # Must match the vector(N) column in supabase/migrations/002_knowledge_chunks.sql
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 1536

    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_max_tokens: int = 1024

    chunk_max_tokens: int = 400
    chunk_overlap_tokens: int = 50
    match_count: int = 5
    # Measured: real questions score 0.66+, off-topic 0.56 or less
    match_threshold: float = 0.6

    # Conversation memory: recent messages within the window are sent with each reply
    history_max_messages: int = 10
    history_window_hours: int = 24

    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    # App secret from Meta App Dashboard > App settings > Basic; used to verify webhook signatures
    whatsapp_app_secret: str = ""
    whatsapp_api_version: str = "v21.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
