import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)
ERROR_KEY = "erro"


class AppError(Exception):
    def __init__(self, status: int, message: str, **extra):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra


class ValidationError(AppError):
    def __init__(self, message: str, **extra):
        super().__init__(400, message, **extra)


class NotFoundError(AppError):
    def __init__(self, message: str, **extra):
        super().__init__(404, message, **extra)


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify({ERROR_KEY: err.message, **err.extra}), err.status

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        if isinstance(err, HTTPException):  # 404/405 do Flask mantêm o comportamento padrão
            return err
        logger.exception("Erro não tratado")
        return jsonify({ERROR_KEY: "Erro interno do servidor"}), 500
