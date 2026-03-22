from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CACHE_DIR: str = "data/cache"
    DATABASE_PATH: str = "data/power2choose.db"
    PDF_DOWNLOAD_TIMEOUT: int = 30
    PDF_DOWNLOAD_MAX_RETRIES: int = 3
    SCANNED_PDF_TEXT_THRESHOLD: int = 50
    PTC_API_URL: str = "https://www.powertochoose.org/en-us/service/v1/"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()


def get_settings() -> Settings:
    return settings
