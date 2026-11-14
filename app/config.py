from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FastAPI RAG Backend"
    api_v1_prefix: str = "/api/v1"

    # Groq exposes an OpenAI-compatible chat completions API (free tier friendly).
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_chat_model: str = "openai/gpt-oss-20b"

    # Groq has no embeddings endpoint, so embeddings run locally via fastembed (no API key, free).
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "rag_documents"
    # If set, Qdrant runs embedded in-process (on-disk, no server/Docker/Cloud needed).
    # Takes precedence over qdrant_url/qdrant_api_key when non-empty.
    qdrant_local_path: str | None = None

    redis_url: str = "redis://localhost:6379/0"

    database_url: str = "sqlite:///./app.db"

    chat_history_ttl_seconds: int = 86400
    chat_history_max_turns: int = 10
    top_k_results: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
