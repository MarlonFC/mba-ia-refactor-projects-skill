import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from database import db

logger = logging.getLogger(__name__)
ERROR_KEY = 'error'  # forma de erro original do projeto: {"error": "..."}


class AppError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class ValidationError(AppError):
    def __init__(self, message):
        super().__init__(400, message)


class NotFoundError(AppError):
    def __init__(self, message):
        super().__init__(404, message)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        db.session.rollback()
        return jsonify({ERROR_KEY: err.message}), err.status

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if isinstance(err, HTTPException):  # 404/405/415 do Flask mantêm o comportamento padrão
            return err
        db.session.rollback()
        logger.exception('Erro não tratado')
        return jsonify({ERROR_KEY: 'Erro interno do servidor'}), 500
