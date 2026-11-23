import logging

from config.settings import DEFAULT_PRIORITY, DEFAULT_STATUS
from controllers.validation import (
    parse_due_date, parse_int_param, require_json, validate_priority, validate_status,
    validate_tags, validate_title,
)
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category
from models.task import Task, completion_rate
from models.user import User
from utils.time import utc_now

logger = logging.getLogger(__name__)


def _get_task_or_404(task_id):
    task = Task.find(task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return task


def _ensure_user_exists(user_id):
    if user_id and not User.find(user_id):
        raise NotFoundError('Usuário não encontrado')


def _ensure_category_exists(category_id):
    if category_id and not Category.find(category_id):
        raise NotFoundError('Categoria não encontrada')


def list_tasks():
    now = utc_now()
    result = []
    for task in Task.list_with_relations():
        data = task.to_dict()
        data['overdue'] = task.is_overdue(now)
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
        result.append(data)
    return result


def get_task(task_id):
    task = _get_task_or_404(task_id)
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return data


def create_task(payload):
    data = require_json(payload)
    title = data.get('title')
    if not title:
        raise ValidationError('Título é obrigatório')
    validate_title(title)

    status = validate_status(data.get('status', DEFAULT_STATUS))
    priority = validate_priority(data.get('priority', DEFAULT_PRIORITY))
    user_id = data.get('user_id')
    category_id = data.get('category_id')
    _ensure_user_exists(user_id)
    _ensure_category_exists(category_id)

    task = Task(title=title, description=data.get('description', ''), status=status,
                priority=priority, user_id=user_id, category_id=category_id)
    if data.get('due_date'):
        task.due_date = parse_due_date(data['due_date'], 'Formato de data inválido. Use YYYY-MM-DD')
    if data.get('tags'):
        task.set_tags(validate_tags(data['tags']))

    task.save()
    logger.info('Task criada: %s - %s', task.id, task.title)
    return task.to_dict()


def update_task(task_id, payload):
    task = _get_task_or_404(task_id)
    data = require_json(payload)

    if 'title' in data:
        task.title = validate_title(data['title'])
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = validate_status(data['status'])
    if 'priority' in data:
        task.priority = validate_priority(data['priority'])
    if 'user_id' in data:
        _ensure_user_exists(data['user_id'])
        task.user_id = data['user_id']
    if 'category_id' in data:
        _ensure_category_exists(data['category_id'])
        task.category_id = data['category_id']
    if 'due_date' in data:
        due_date = data['due_date']
        task.due_date = parse_due_date(due_date, 'Formato de data inválido') if due_date else None
    if 'tags' in data:
        task.set_tags(validate_tags(data['tags']))

    task.updated_at = utc_now()
    task.save()
    logger.info('Task atualizada: %s', task.id)
    return task.to_dict()


def delete_task(task_id):
    task = _get_task_or_404(task_id)
    task.delete()
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
    total = Task.count()
    by_status = Task.count_by(Task.status)
    now = utc_now()
    overdue = sum(1 for task in Task.list_all() if task.is_overdue(now))
    done = by_status.get('done', 0)
    return {
        'total': total,
        'pending': by_status.get('pending', 0),
        'in_progress': by_status.get('in_progress', 0),
        'done': done,
        'cancelled': by_status.get('cancelled', 0),
        'overdue': overdue,
        'completion_rate': completion_rate(done, total),
    }
