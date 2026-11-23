import hashlib
import hmac

from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from config.settings import DEFAULT_ROLE
from database import db
from models.task import Task
from utils.time import utc_now


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        # A senha (hash) nunca é serializada.
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    # ---- senha ----
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def _has_legacy_hash(self):
        # Hashes do Werkzeug têm formato "metodo$salt$hash"; o legado é MD5 hex puro.
        return '$' not in (self.password or '')

    def check_password(self, password):
        if not self._has_legacy_hash():
            return check_password_hash(self.password, password)
        legacy = hashlib.md5(password.encode()).hexdigest()
        if not hmac.compare_digest(self.password, legacy):
            return False
        # Migração transparente: regrava com o hash seguro.
        self.set_password(password)
        db.session.commit()
        return True

    # ---- persistência ----
    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete_with_tasks(self):
        """Remove o usuário e suas tasks na mesma transação (comportamento original)."""
        for task in Task.query.filter_by(user_id=self.id).all():
            db.session.delete(task)
        db.session.delete(self)
        db.session.commit()

    # ---- consultas ----
    @classmethod
    def find(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def list_all(cls):
        return cls.query.order_by(cls.id).all()

    @classmethod
    def count(cls):
        return cls.query.count()

    @staticmethod
    def task_counts():
        """{user_id: quantidade de tasks} em uma única query."""
        return dict(db.session.query(Task.user_id, func.count(Task.id)).group_by(Task.user_id).all())

    @staticmethod
    def done_task_counts():
        """{user_id: quantidade de tasks concluídas} em uma única query."""
        return dict(db.session.query(Task.user_id, func.count(Task.id))
                    .filter(Task.status == 'done').group_by(Task.user_id).all())
