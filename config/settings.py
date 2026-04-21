from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_GENERATION_MODEL: str = "gpt-4o"
    OPENAI_GRADER_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "dell-rag-platform"

    STORAGE_BASE_PATH: str = "./storage"
    MASTER_DB_PATH: str = "./storage/tenants.db"

    REDIS_URL: str = "redis://localhost:6379/0"

    PLATFORM_ADMIN_KEY: str = "change-me"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
