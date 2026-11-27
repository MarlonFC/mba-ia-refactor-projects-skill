"""Validação de entrada na borda (mesmas mensagens do contrato original)."""
from datetime import datetime

from config.settings import DUE_DATE_FORMAT, MAX_PRIORITY, MAX_TITLE_LENGTH, MIN_PRIORITY, MIN_TITLE_LENGTH, TASK_STATUSES
from middlewares.error_handler import NotFoundError, ValidationError


def require_json(payload):
    if not payload or not isinstance(payload, dict):
        raise ValidationError('Dados inválidos')
    return payload


def validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def validate_status(status):
    if status not in TASK_STATUSES:
        raise ValidationError('Status inválido')
    return status


def validate_priority(priority):
    if isinstance(priority, bool) or not isinstance(priority, (int, float)):
        raise ValidationError('Prioridade inválida')
    if not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise ValidationError(f'Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}')
    return priority


def parse_due_date(value, error_message):
    try:
        return datetime.strptime(value, DUE_DATE_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError(error_message) from None


def parse_int_param(value, field):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError(f'Parâmetro {field} inválido') from None


def require_found(entity, message):
    if entity is None:
        raise NotFoundError(message)
    return entity
