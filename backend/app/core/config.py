from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "智服云 · 电商智能客服"
    database_url: str = f"sqlite:///{ROOT / 'data' / 'zhifu.db'}"
    # Do NOT name this MILVUS_URI — pymilvus reads that env var globally on import.
    vector_uri: str = str((ROOT / "data" / "milvus.db").resolve())
    milvus_collection: str = "kb_chunks"
    jwt_secret: str = "zhifu-dev-secret-change-me"
    jwt_expire_minutes: int = 1440
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    embedding_base_url: str = "http://127.0.0.1:11434/v1"
    embedding_model: str = "qwen3-embedding:0.6b"
    llm_mock: bool = True
    upload_dir: str = str(ROOT / "uploads" / "docs")
    cors_origins: str = "http://127.0.0.1:18765,http://localhost:18765"
    embedding_dim: int = 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
