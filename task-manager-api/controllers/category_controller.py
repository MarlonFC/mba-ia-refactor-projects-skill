from config.settings import DEFAULT_CATEGORY_COLOR
from controllers.validation import require_found, require_json
from database import db
from middlewares.error_handler import ValidationError
from models.category import Category
from models.task import Task

CATEGORY_NOT_FOUND = 'Categoria não encontrada'


def list_categories():
    task_counts = Category.task_counts()
    result = []
    for category in Category.all_ordered():
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
        name=name,
        description=data.get('description', ''),
        color=data.get('color', DEFAULT_CATEGORY_COLOR),
    )
    db.session.add(category)
    db.session.commit()
    return category.to_dict()


def update_category(category_id, payload):
    category = require_found(Category.find(category_id), CATEGORY_NOT_FOUND)
    data = require_json(payload)
    for field in ('name', 'description', 'color'):
        if field in data:
            setattr(category, field, data[field])
    db.session.commit()
    return category.to_dict()


def delete_category(category_id):
    category = require_found(Category.find(category_id), CATEGORY_NOT_FOUND)
    Task.unlink_category(category_id)  # tasks continuam existindo, sem categoria órfã
    db.session.delete(category)
    db.session.commit()
