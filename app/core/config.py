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
    match_threshold: float = 0.3

    # Conversation memory: recent messages within the window are sent with each reply
    history_max_messages: int = 10
    history_window_hours: int = 24

    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_api_version: str = "v21.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
