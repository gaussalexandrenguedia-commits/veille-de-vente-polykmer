"""Configuration centrale (variables d'environnement)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
ROOT_DIR = BACKEND_DIR.parent                          # racine du repo


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite démo par défaut (zéro config) ; Postgres via .env en prod :
    # postgresql+psycopg2://veille:veille_pw@localhost:5432/veille_vente
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'veille_demo.db'}"
    API_KEY_INGEST: str = "changez-moi-cle-ingest"
    KOBO_TOKEN: str = ""
    CORS_ORIGINS: str = "http://localhost:8501,http://localhost:3000"
    APP_NAME: str = "Veille Vente CM & CEMAC"
    # Intégration sniper (lecture seule, optionnelle)
    SNIPER_STATE_DB: str = str(ROOT_DIR / "sniper" / "state" / "sniper.db")
    SNIPER_CONFIG: str = str(ROOT_DIR / "sniper" / "config" / "watches.yaml")


settings = Settings()
