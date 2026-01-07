from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./pelles.db"

    # Cache settings
    cache_ttl_days: int = 7

    # Scraper settings
    scraper_delay_seconds: float = 1.5
    scraper_max_results: int = 10
    scraper_timeout_seconds: int = 30

    # Matching settings
    match_high_threshold: float = 0.85
    match_medium_threshold: float = 0.60
    min_coverage_for_recommendation: float = 0.70

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
