import logging

from config.settings import DEFAULT_PRIORITY, DEFAULT_TASK_STATUS
from controllers.validation import (
    parse_due_date,
    parse_int_param,
    require_found,
    require_json,
    validate_priority,
    validate_status,
    validate_title,
)
from database import db
from middlewares.error_handler import ValidationError
from models import report
from models.category import Category
from models.task import Task
from models.user import User
from utils.time import utc_now

logger = logging.getLogger(__name__)

TASK_NOT_FOUND = 'Task não encontrada'


def _ensure_user_exists(user_id):
    if user_id:
        require_found(User.find(user_id), 'Usuário não encontrado')


def _ensure_category_exists(category_id):
    if category_id:
        require_found(Category.find(category_id), 'Categoria não encontrada')


def list_tasks():
    result = []
    for task in Task.all_with_relations():
        data = task.to_dict_with_overdue()
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
        result.append(data)
    return result


def get_task(task_id):
    return require_found(Task.find(task_id), TASK_NOT_FOUND).to_dict_with_overdue()


def create_task(payload):
    data = require_json(payload)
    title = data.get('title')
    if not title:
        raise ValidationError('Título é obrigatório')
    validate_title(title)
    status = validate_status(data.get('status', DEFAULT_TASK_STATUS))
    priority = validate_priority(data.get('priority', DEFAULT_PRIORITY))
    _ensure_user_exists(data.get('user_id'))
    _ensure_category_exists(data.get('category_id'))

    task = Task(
        title=title,
        description=data.get('description', ''),
        status=status,
        priority=priority,
        user_id=data.get('user_id'),
        category_id=data.get('category_id'),
    )
    if data.get('due_date'):
        task.due_date = parse_due_date(data['due_date'], 'Formato de data inválido. Use YYYY-MM-DD')
    if data.get('tags'):
        task.tags = Task.serialize_tags(data['tags'])

    db.session.add(task)
    db.session.commit()
    logger.info('Task criada: %s - %s', task.id, task.title)
    return task.to_dict()


def update_task(task_id, payload):
    task = require_found(Task.find(task_id), TASK_NOT_FOUND)
    data = require_json(payload)

    changes = {}
    if 'title' in data:
        changes['title'] = validate_title(data['title'])
    if 'description' in data:
        changes['description'] = data['description']
    if 'status' in data:
        changes['status'] = validate_status(data['status'])
    if 'priority' in data:
        changes['priority'] = validate_priority(data['priority'])
    if 'user_id' in data:
        _ensure_user_exists(data['user_id'])
        changes['user_id'] = data['user_id']
    if 'category_id' in data:
        _ensure_category_exists(data['category_id'])
        changes['category_id'] = data['category_id']
    if 'due_date' in data:
        changes['due_date'] = (
            parse_due_date(data['due_date'], 'Formato de data inválido') if data['due_date'] else None
        )
    if 'tags' in data:
        changes['tags'] = Task.serialize_tags(data['tags'])

    for field, value in changes.items():
        setattr(task, field, value)
    task.updated_at = utc_now()
    db.session.commit()
    logger.info('Task atualizada: %s', task.id)
    return task.to_dict()


def delete_task(task_id):
    task = require_found(Task.find(task_id), TASK_NOT_FOUND)
    db.session.delete(task)
    db.session.commit()
    logger.info('Task deletada: %s', task_id)


def search_tasks(text, status, priority, user_id):
    tasks = Task.search(
        text=text,
        status=status,
        priority=parse_int_param(priority, 'priority'),
        user_id=parse_int_param(user_id, 'user_id'),
    )
    return [task.to_dict() for task in tasks]


def task_stats():
    return report.task_stats()
