from controllers.validation import require_found
from models import report
from models.user import User


def summary_report():
    return report.summary()


def user_report(user_id):
    user = require_found(User.find(user_id), 'Usuário não encontrado')
    return report.user_statistics(user)
