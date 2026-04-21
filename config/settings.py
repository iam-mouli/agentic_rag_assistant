from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Provider selection ---
    LLM_PROVIDER: str = "openai"        # openai | anthropic | gemini
    EMBEDDING_PROVIDER: str = "openai"  # openai | gemini  (Anthropic has no embedding model)

    # --- OpenAI ---
    OPENAI_API_KEY: str = ""
    OPENAI_GENERATION_MODEL: str = "gpt-4o"
    OPENAI_GRADER_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # --- Anthropic ---
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_GENERATION_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_GRADER_MODEL: str = "claude-haiku-4-5-20251001"

    # --- Google Gemini ---
    GOOGLE_API_KEY: str = ""
    GOOGLE_GENERATION_MODEL: str = "gemini-2.0-flash"
    GOOGLE_GRADER_MODEL: str = "gemini-2.0-flash-lite"
    GOOGLE_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # --- Observability ---
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "agentic-rag-platform"

    # --- Storage ---
    STORAGE_BASE_PATH: str = "./storage"
    MASTER_DB_PATH: str = "./storage/tenants.db"

    # --- Redis (cache, rate-limits, arq queue, FAISS write locks) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Platform ---
    PLATFORM_ADMIN_KEY: str = "change-me"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
