"""Configuration centrale (variables d'environnement)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://veille:veille_pw@localhost:5432/veille_vente"
    API_KEY_INGEST: str = "changez-moi-cle-ingest"
    KOBO_TOKEN: str = ""
    CORS_ORIGINS: str = "http://localhost:8501,http://localhost:3000"
    APP_NAME: str = "Veille Vente CM & CEMAC"


settings = Settings()
