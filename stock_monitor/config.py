import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    broker_url: str
    brapi_base_url: str
    brapi_token: str | None
    celery_timezone: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv('DATABASE_URL', 'sqlite:///./data/stocks.db'),
        broker_url=os.getenv('BROKER_URL', 'amqp://guest:guest@localhost:5672//'),
        brapi_base_url=os.getenv('BRAPI_BASE_URL', 'https://brapi.dev/api'),
        brapi_token=os.getenv('BRAPI_TOKEN'),
        celery_timezone=os.getenv('CELERY_TIMEZONE', 'America/Sao_Paulo'),
    )
