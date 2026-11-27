import hashlib
import hmac

from sqlalchemy import case, func
from werkzeug.security import check_password_hash, generate_password_hash

from config.settings import ADMIN_ROLE, DEFAULT_ROLE, DONE_STATUS
from database import db
from utils.time import utc_now

MODERN_HASH_PREFIXES = ('scrypt:', 'pbkdf2:')


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
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Verifica a senha; hashes MD5 legados são aceitos e regravados no formato novo."""
        if self.password.startswith(MODERN_HASH_PREFIXES):
            return check_password_hash(self.password, raw_password)
        legacy_hash = hashlib.md5(raw_password.encode()).hexdigest()
        if not hmac.compare_digest(self.password, legacy_hash):
            return False
        self.set_password(raw_password)
        return True

    def is_admin(self):
        return self.role == ADMIN_ROLE

    # --- consultas ---
    @classmethod
    def find(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def all_ordered(cls):
        return cls.query.order_by(cls.id).all()

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @staticmethod
    def task_counts():
        """{user_id: (total, concluídas)} em uma única query agregada."""
        from models.task import Task

        rows = (
            db.session.query(
                Task.user_id,
                func.count(Task.id),
                func.sum(case((Task.status == DONE_STATUS, 1), else_=0)),
            )
            .filter(Task.user_id.isnot(None))
            .group_by(Task.user_id)
            .all()
        )
        return {user_id: (total, int(done or 0)) for user_id, total, done in rows}
