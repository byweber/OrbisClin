"""
config.py — Configurações centralizadas com validação via pydantic-settings.
"""
import secrets
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_VERSION: str = "8.0"
    APP_NAME: str = "OrbisClin"

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DATABASE_URL: str = "sqlite:///./orbisclin.db"
    STORAGE_DIR: str = "./storage"

    ORTHANC_URL: str = "http://localhost:8042"
    ORTHANC_USER: str = "orthanc"
    ORTHANC_PASS: str = "orthanc"

    REDIS_URL: str = "redis://localhost:6379/0"

    def get_secret_key(self) -> str:
        if not self.SECRET_KEY:
            import logging
            logging.warning(
                "⚠️  SECRET_KEY não definida no .env! "
                "Usando chave temporária — tokens serão invalidados ao reiniciar."
            )
            return secrets.token_hex(32)
        return self.SECRET_KEY


@lru_cache
def get_settings() -> Settings:
    return Settings()
