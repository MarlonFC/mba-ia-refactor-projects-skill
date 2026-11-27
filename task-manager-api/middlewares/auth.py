import hmac
from functools import wraps

from flask import current_app, request
from itsdangerous import URLSafeTimedSerializer

from middlewares.error_handler import AppError

ADMIN_HEADER = 'X-Admin-Token'
LOGIN_TOKEN_SALT = 'login'


def issue_login_token(user_id):
    """Token de login assinado com SECRET_KEY (substitui o antigo 'fake-jwt-token-<id>')."""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=LOGIN_TOKEN_SALT).dumps({'uid': user_id})


def has_valid_admin_token():
    expected = current_app.config.get('ADMIN_TOKEN')
    provided = request.headers.get(ADMIN_HEADER, '')
    return bool(expected) and hmac.compare_digest(provided.encode(), expected.encode())


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not has_valid_admin_token():
            raise AppError(401, 'Não autorizado')
        return view(*args, **kwargs)
    return wrapper
