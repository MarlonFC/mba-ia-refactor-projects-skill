"""Casos de uso de infraestrutura: health check e operações administrativas."""
import logging

from flask import current_app

from config.settings import API_VERSION
from controllers.validation import exigir_objeto
from middlewares.error_handler import ValidationError
from models import sistema_model

logger = logging.getLogger(__name__)


def health() -> dict:
    return {
        "status": "ok",
        "database": "connected",
        "counts": sistema_model.contagens(),
        "versao": API_VERSION,
        "ambiente": current_app.config["ENVIRONMENT"],
        "db_path": current_app.config["DATABASE_PATH"],
        "debug": current_app.debug,
    }


def resetar_banco() -> None:
    sistema_model.resetar()
    logger.warning("Banco de dados resetado")


def executar_query(dados) -> list[dict] | None:
    dados = exigir_objeto(dados, aceita_vazio=True)
    sql = dados.get("sql", "")
    if not isinstance(sql, str) or not sql:
        raise ValidationError("Query não informada")
    try:
        return sistema_model.executar_sql(sql)
    except sistema_model.QueryInvalidaError:
        logger.exception("Falha na query administrativa")
        raise ValidationError("Query inválida") from None
