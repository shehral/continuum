from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://continuum:password@localhost:5432/continuum"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4jpassword"
    redis_url: str = "redis://localhost:6379"

    # AI Provider (NVIDIA NIM)
    nvidia_api_key: str = ""  # Set via NVIDIA_API_KEY env var
    nvidia_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1.5"

    # Embedding Model (NVIDIA NV-EmbedQA)
    nvidia_embedding_api_key: str = ""  # Set via NVIDIA_EMBEDDING_API_KEY env var
    nvidia_embedding_model: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"

    # Rate limiting
    rate_limit_requests: int = 30  # requests per minute
    rate_limit_window: int = 60  # seconds

    # Paths
    claude_logs_path: str = "~/.claude/projects"

    # Auth
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # App
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
