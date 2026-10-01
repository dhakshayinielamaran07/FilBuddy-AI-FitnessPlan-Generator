from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitBuddy"
    gemini_api_key: str = ""
    gemini_workout_model: str = "gemini-3.8-flash"
    gemini_nutrition_model: str = "gemini-3.5-flash"
    mock_ai: bool = False
    database_url: str = "sqlite:///./fitbuddy.db"
    max_feedback_length: int = 2000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
