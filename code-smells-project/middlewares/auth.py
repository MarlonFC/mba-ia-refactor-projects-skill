"""Proteção de rotas administrativas por token (header X-Admin-Token)."""
import hmac
from functools import wraps

from flask import current_app, request

from middlewares.error_handler import AppError


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN")
        provided = request.headers.get("X-Admin-Token", "")
        if not expected or not hmac.compare_digest(provided.encode(), expected.encode()):
            raise AppError(401, "Não autorizado")
        return view(*args, **kwargs)

    return wrapper
