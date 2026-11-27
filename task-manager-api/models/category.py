from sqlalchemy import func

from config.settings import DEFAULT_CATEGORY_COLOR
from database import db
from utils.time import utc_now


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_CATEGORY_COLOR)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'created_at': str(self.created_at),
        }

    # --- consultas ---
    @classmethod
    def find(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def all_ordered(cls):
        return cls.query.order_by(cls.id).all()

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @staticmethod
    def task_counts():
        """{category_id: nº de tasks} em uma única query agregada."""
        from models.task import Task

        rows = db.session.query(Task.category_id, func.count(Task.id)).group_by(Task.category_id).all()
        return dict(rows)
