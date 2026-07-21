from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    app_name: str = "SME Credit Risk API"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "sqlite:///./data/sme_credit.db"

    secret_key: str = "dev-secret-key-change-in-production"
    pseudonymization_key: str = "dev-pseudonymization-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 240

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://ushirika-sme-portal.vercel.app,"
        "https://ushirika-sme-portal-dmmkuliku.vercel.app"
    )

    model_dir: str = "./models"
    min_transactions_for_score: int = 5
    random_seed: int = 42

    max_financing_tzs: float = 50_000_000.0
    min_financing_tzs: float = 500_000.0

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
