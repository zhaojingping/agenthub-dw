from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/agenthub"

    # AI API
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    dashscope_api_key: str = ""
    wenxin_api_key: str = ""
    wenxin_secret_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
