from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    APP_NAME: str = "TP_TRAVEL_AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vector_db"
    REDIS_URL: Optional[str] = None

    # LLM Provider Configuration
    LLM_PROVIDER: str = "ollama"  # ollama | gemini | openai | mock
    LLM_MODEL_NAME: str = "llama3:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_TIMEOUT_SECONDS: float = 30.0

    # Embedding Provider Configuration
    EMBEDDING_PROVIDER: str = "local"  # local | openai
    EMBEDDING_MODEL_NAME: str = "jhgan/ko-sroberta-multitask"
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_DEVICE: str = "cpu"

    # Chunking
    DEFAULT_CHUNK_SIZE: int = 500
    DEFAULT_CHUNK_OVERLAP: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

