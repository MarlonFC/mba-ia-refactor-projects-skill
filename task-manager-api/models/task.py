from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config.settings import CLOSED_TASK_STATUSES, DEFAULT_PRIORITY, DEFAULT_TASK_STATUS, DONE_STATUS
from database import db
from utils.time import utc_now


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=DEFAULT_TASK_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    def to_dict_with_overdue(self):
        data = self.to_dict()
        data['overdue'] = self.is_overdue()
        return data

    def to_summary_dict(self):
        """Formato resumido usado em GET /users/<id>/tasks."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': str(self.created_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'overdue': self.is_overdue(),
        }

    def is_overdue(self, now=None):
        if not self.due_date or self.status in CLOSED_TASK_STATUSES:
            return False
        return self.due_date < (now or utc_now())

    @staticmethod
    def serialize_tags(tags):
        return ','.join(tags) if isinstance(tags, list) else tags

    # --- consultas ---
    @classmethod
    def find(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def all_ordered(cls):
        return cls.query.order_by(cls.id).all()

    @classmethod
    def all_with_relations(cls):
        return cls.query.options(joinedload(cls.user), joinedload(cls.category)).order_by(cls.id).all()

    @classmethod
    def by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).order_by(cls.id).all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        query = cls.query
        if text:
            pattern = f'%{text}%'
            query = query.filter(db.or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            query = query.filter(cls.status == status)
        if priority is not None:
            query = query.filter(cls.priority == priority)
        if user_id is not None:
            query = query.filter(cls.user_id == user_id)
        return query.order_by(cls.id).all()

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def count_by(cls, column):
        """Contagens agrupadas por coluna em uma única query (ex.: status, priority)."""
        return dict(db.session.query(column, func.count(cls.id)).group_by(column).all())

    @classmethod
    def overdue(cls, now):
        return (
            cls.query
            .filter(cls.due_date.isnot(None), cls.due_date < now, cls.status.notin_(CLOSED_TASK_STATUSES))
            .order_by(cls.id)
            .all()
        )

    @classmethod
    def count_created_since(cls, since):
        return cls.query.filter(cls.created_at >= since).count()

    @classmethod
    def count_completed_since(cls, since):
        return cls.query.filter(cls.status == DONE_STATUS, cls.updated_at >= since).count()

    @classmethod
    def unlink_category(cls, category_id):
        cls.query.filter_by(category_id=category_id).update({'category_id': None})

    @classmethod
    def delete_by_user(cls, user_id):
        cls.query.filter_by(user_id=user_id).delete()
