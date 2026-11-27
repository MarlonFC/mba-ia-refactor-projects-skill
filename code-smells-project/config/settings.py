import os
import secrets


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class Settings:
    # Sem segredo literal: usa env ou gera um efêmero a cada boot.
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _env_bool("FLASK_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
    # Sem default: rotas admin ficam fechadas (401) até ADMIN_TOKEN ser configurado.
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
    CORS_ORIGINS = _env_list("CORS_ORIGINS", "http://localhost:5000")
    AMBIENTE = os.getenv("APP_ENV", "producao")
    VERSAO = "1.0.0"
