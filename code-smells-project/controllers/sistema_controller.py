import logging

from flask import current_app

from models import sistema_model

logger = logging.getLogger(__name__)


def health() -> dict:
    return {
        "status": "ok",
        "database": "connected",
        "counts": sistema_model.contagens(),
        "versao": current_app.config["VERSAO"],
        "ambiente": current_app.config["AMBIENTE"],
    }


def resetar_banco() -> None:
    sistema_model.resetar_banco()
    logger.warning("!!! BANCO DE DADOS RESETADO !!!")
