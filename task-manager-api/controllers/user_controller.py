import logging

from config.settings import DEFAULT_ROLE, MIN_PASSWORD_LENGTH
from controllers.validation import (
    require_json, validate_active, validate_email, validate_name, validate_password_length,
    validate_role,
)
from middlewares.error_handler import (
    ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError,
)
from models.task import Task
from models.user import User

logger = logging.getLogger(__name__)


def _get_user_or_404(user_id):
    user = User.find(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')
    return user


def _ensure_email_available(email, current_user_id=None):
    existing = User.find_by_email(email)
    if existing and existing.id != current_user_id:
        raise ConflictError('Email já cadastrado')


def list_users():
    task_counts = User.task_counts()
    result = []
    for user in User.list_all():
        data = user.to_dict()
        data['task_count'] = task_counts.get(user.id, 0)
        result.append(data)
    return result


def get_user(user_id):
    user = _get_user_or_404(user_id)
    data = user.to_dict()
    data['tasks'] = [task.to_dict() for task in Task.list_by_user(user_id)]
    return data


def create_user(payload):
    data = require_json(payload)
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', DEFAULT_ROLE)

    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    validate_email(email)
    validate_password_length(password, MIN_PASSWORD_LENGTH,
                             f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres')
    _ensure_email_available(email)
    validate_role(role)

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    user.save()
    logger.info('Usuário criado: %s', user.id)
    return user.to_dict()


def update_user(user_id, payload):
    user = _get_user_or_404(user_id)
    data = require_json(payload)

    if 'name' in data:
        user.name = validate_name(data['name'])
    if 'email' in data:
        validate_email(data['email'])
        _ensure_email_available(data['email'], current_user_id=user_id)
        user.email = data['email']
    if 'password' in data:
        validate_password_length(data['password'], MIN_PASSWORD_LENGTH, 'Senha muito curta')
        user.set_password(data['password'])
    if 'role' in data:
        user.role = validate_role(data['role'])
    if 'active' in data:
        user.active = validate_active(data['active'])

    user.save()
    return user.to_dict()


def delete_user(user_id):
    user = _get_user_or_404(user_id)
    user.delete_with_tasks()
    logger.info('Usuário deletado: %s', user_id)


def list_user_tasks(user_id):
    _get_user_or_404(user_id)
    return [task.to_summary_dict() for task in Task.list_by_user(user_id)]


def login(payload):
    data = require_json(payload)
    email = data.get('email')
    password = data.get('password')
    if not email or not password or not isinstance(password, str):
        raise ValidationError('Email e senha são obrigatórios')

    user = User.find_by_email(email)
    if not user or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        # Token não assinado mantido por contrato — ver F-05 (deferred).
        'token': f'fake-jwt-token-{user.id}',
    }
