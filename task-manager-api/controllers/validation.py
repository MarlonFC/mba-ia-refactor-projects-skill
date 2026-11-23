"""Validação de entrada compartilhada entre os controllers (mensagens = contrato original)."""
import re
from datetime import datetime

from config.settings import (
    DUE_DATE_FORMAT, EMAIL_PATTERN, PRIORITY_MAX, PRIORITY_MIN, TASK_STATUSES,
    TITLE_MAX_LENGTH, TITLE_MIN_LENGTH, USER_ROLES,
)
from middlewares.error_handler import ValidationError


def require_json(payload, allow_empty=False):
    if not isinstance(payload, dict) or (not payload and not allow_empty):
        raise ValidationError('Dados inválidos')
    return payload


def validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < TITLE_MIN_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > TITLE_MAX_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def validate_status(status):
    if status not in TASK_STATUSES:
        raise ValidationError('Status inválido')
    return status


def validate_priority(priority):
    valid_int = isinstance(priority, int) and not isinstance(priority, bool)
    if not valid_int or not PRIORITY_MIN <= priority <= PRIORITY_MAX:
        raise ValidationError(f'Prioridade deve ser entre {PRIORITY_MIN} e {PRIORITY_MAX}')
    return priority


def parse_due_date(value, error_message):
    try:
        return datetime.strptime(value, DUE_DATE_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError(error_message) from None


def validate_tags(tags):
    if tags is None or isinstance(tags, str):
        return tags
    if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
        return tags
    raise ValidationError('Tags inválidas')


def parse_int_param(value, field):
    """Converte parâmetro de query string; vazio/ausente → None."""
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError(f'Parâmetro {field} inválido') from None


def validate_email(email):
    if not isinstance(email, str) or not re.match(EMAIL_PATTERN, email):
        raise ValidationError('Email inválido')
    return email


def validate_password_length(password, min_length, message):
    if not isinstance(password, str) or len(password) < min_length:
        raise ValidationError(message)
    return password


def validate_role(role):
    if role not in USER_ROLES:
        raise ValidationError('Role inválido')
    return role


def validate_name(name):
    if not isinstance(name, str):
        raise ValidationError('Nome é obrigatório')
    return name


def validate_active(active):
    if not isinstance(active, bool) and active not in (0, 1):
        raise ValidationError('Campo active deve ser booleano')
    return active
