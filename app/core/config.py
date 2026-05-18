from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    app_name: str = "DOCNTEL AI"
    database_url: str

    model_config = SettingsConfigDict(env_file=".env")

    secret_key: SecretStr
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    qdrant_cloud_url: str
    qdrant_cloud_api_key: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
