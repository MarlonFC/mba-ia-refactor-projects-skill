from sqlalchemy import func

from config.settings import DEFAULT_CATEGORY_COLOR
from database import db
from models.task import Task
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

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete_unlinking_tasks(self):
        """Tasks são independentes da categoria: desvincula (category_id = NULL) e remove, na mesma transação."""
        Task.query.filter_by(category_id=self.id).update({'category_id': None})
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def list_all(cls):
        return cls.query.order_by(cls.id).all()

    @classmethod
    def count(cls):
        return cls.query.count()

    @staticmethod
    def task_counts():
        """{category_id: quantidade de tasks} em uma única query."""
        return dict(db.session.query(Task.category_id, func.count(Task.id)).group_by(Task.category_id).all())
