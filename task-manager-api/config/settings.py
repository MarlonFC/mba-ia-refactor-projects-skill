"""Configuração da aplicação (variáveis de ambiente) e constantes de domínio."""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name, default=''):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


class Settings:
    # Sem segredo literal: usa env ou gera um efêmero (tokens invalidam a cada restart).
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = _env_bool('APP_DEBUG', False)
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', '5000'))
    ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')  # sem default: rotas admin fechadas
    CORS_ORIGINS = _env_list('CORS_ORIGINS')  # vazio = nenhuma origem externa liberada


# --- Constantes de domínio ---
TASK_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
DONE_STATUS = 'done'
CLOSED_TASK_STATUSES = (DONE_STATUS, 'cancelled')
DEFAULT_TASK_STATUS = 'pending'
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2  # prioridades 1 e 2 contam como "alta"
PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}
DUE_DATE_FORMAT = '%Y-%m-%d'
RECENT_ACTIVITY_DAYS = 7

USER_ROLES = ('user', 'admin', 'manager')
DEFAULT_ROLE = 'user'
ADMIN_ROLE = 'admin'
MIN_PASSWORD_LENGTH = 4

DEFAULT_CATEGORY_COLOR = '#000000'
