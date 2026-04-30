from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./data/uploads"

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    allow_registration: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    chunk_size_tokens: int = 800
    chunk_overlap_tokens: int = 100
    rag_top_k: int = 8
    rag_keyword_k: int = 6  # FTS5 hits to mix in alongside vector matches
    chat_history_turns: int = 6

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
