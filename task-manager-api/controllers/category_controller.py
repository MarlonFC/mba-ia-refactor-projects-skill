from config.settings import DEFAULT_CATEGORY_COLOR
from controllers.validation import require_json, validate_name
from middlewares.error_handler import NotFoundError, ValidationError
from models.category import Category


def _get_category_or_404(category_id):
    category = Category.find(category_id)
    if not category:
        raise NotFoundError('Categoria não encontrada')
    return category


def list_categories():
    task_counts = Category.task_counts()
    result = []
    for category in Category.list_all():
        data = category.to_dict()
        data['task_count'] = task_counts.get(category.id, 0)
        result.append(data)
    return result


def create_category(payload):
    data = require_json(payload)
    name = data.get('name')
    if not name:
        raise ValidationError('Nome é obrigatório')
    category = Category(
        name=validate_name(name),
        description=data.get('description', ''),
        color=data.get('color', DEFAULT_CATEGORY_COLOR),
    )
    category.save()
    return category.to_dict()


def update_category(category_id, payload):
    category = _get_category_or_404(category_id)
    data = require_json(payload, allow_empty=True)
    if 'name' in data:
        category.name = validate_name(data['name'])
    if 'description' in data:
        category.description = data['description']
    if 'color' in data:
        category.color = data['color']
    category.save()
    return category.to_dict()


def delete_category(category_id):
    _get_category_or_404(category_id).delete_unlinking_tasks()
