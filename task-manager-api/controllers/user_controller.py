import logging

from config.settings import DEFAULT_ROLE, MIN_PASSWORD_LENGTH, USER_ROLES
from controllers.validation import require_found, require_json
from database import db
from middlewares.auth import issue_login_token
from middlewares.error_handler import AppError, ValidationError
from models.task import Task
from models.user import User
from utils.helpers import validate_email

logger = logging.getLogger(__name__)

USER_NOT_FOUND = 'Usuário não encontrado'
PRIVILEGED_FIELDS = ('role', 'active')


def _is_short_password(password):
    return not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH


def _ensure_email_available(email, current_user_id=None):
    existing = User.find_by_email(email)
    if existing and existing.id != current_user_id:
        raise AppError(409, 'Email já cadastrado')


def _validate_role(role):
    if role not in USER_ROLES:
        raise ValidationError('Role inválido')
    return role


def list_users():
    task_counts = User.task_counts()
    result = []
    for user in User.all_ordered():
        data = user.to_dict()
        data['task_count'] = task_counts.get(user.id, (0, 0))[0]
        result.append(data)
    return result


def get_user(user_id):
    user = require_found(User.find(user_id), USER_NOT_FOUND)
    data = user.to_dict()
    data['tasks'] = [task.to_dict() for task in Task.by_user(user_id)]
    return data


def create_user(payload, is_admin_request):
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
    if not validate_email(email):
        raise ValidationError('Email inválido')
    if _is_short_password(password):
        raise ValidationError(f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres')
    _ensure_email_available(email)
    _validate_role(role)
    if role != DEFAULT_ROLE and not is_admin_request:
        raise AppError(403, 'Somente administradores podem definir role')

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    logger.info('Usuário criado: %s', user.id)
    return user.to_dict()


def update_user(user_id, payload, is_admin_request):
    user = require_found(User.find(user_id), USER_NOT_FOUND)
    data = require_json(payload)
    if not is_admin_request and any(field in data for field in PRIVILEGED_FIELDS):
        raise AppError(403, 'Somente administradores podem alterar role ou active')

    changes = {}
    if 'name' in data:
        changes['name'] = data['name']
    if 'email' in data:
        if not validate_email(data['email']):
            raise ValidationError('Email inválido')
        _ensure_email_available(data['email'], current_user_id=user_id)
        changes['email'] = data['email']
    if 'password' in data and _is_short_password(data['password']):
        raise ValidationError('Senha muito curta')
    if 'role' in data:
        changes['role'] = _validate_role(data['role'])
    if 'active' in data:
        changes['active'] = data['active']

    for field, value in changes.items():
        setattr(user, field, value)
    if 'password' in data:
        user.set_password(data['password'])
    db.session.commit()
    return user.to_dict()


def delete_user(user_id):
    user = require_found(User.find(user_id), USER_NOT_FOUND)
    Task.delete_by_user(user_id)  # tasks pertencem ao usuário (comportamento original)
    db.session.delete(user)
    db.session.commit()
    logger.info('Usuário deletado: %s', user_id)


def list_user_tasks(user_id):
    require_found(User.find(user_id), USER_NOT_FOUND)
    return [task.to_summary_dict() for task in Task.by_user(user_id)]


def login(payload):
    data = require_json(payload)
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')

    user = User.find_by_email(email)
    if not user or not isinstance(password, str) or not user.check_password(password):
        raise AppError(401, 'Credenciais inválidas')
    db.session.commit()  # persiste a migração transparente de hash legado, se houve
    if not user.active:
        raise AppError(403, 'Usuário inativo')

    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': issue_login_token(user.id),
    }
