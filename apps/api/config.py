from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database - all credentials must be set via environment variables
    database_url: str = ""  # e.g., postgresql+asyncpg://user:pass@localhost:5432/dbname

    @field_validator("database_url", mode="after")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """Convert postgresql:// to postgresql+asyncpg:// for async support."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    neo4j_uri: str = ""  # e.g., bolt://localhost:7687 or neo4j+s://xxx.databases.neo4j.io
    neo4j_user: str = ""
    neo4j_password: str = ""
    redis_url: str = ""  # e.g., redis://localhost:6379

    # AI Provider (NVIDIA NIM)
    nvidia_api_key: str = ""
    nvidia_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1.5"

    # Embedding Model (NVIDIA NV-EmbedQA)
    nvidia_embedding_api_key: str = ""
    nvidia_embedding_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"

    # Rate limiting
    rate_limit_requests: int = 30  # requests per minute
    rate_limit_window: int = 60  # seconds

    # Paths
    claude_logs_path: str = "~/.claude/projects"

    # Auth - must be set in production
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # App
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
