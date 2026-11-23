from datetime import timedelta

from config.settings import HIGH_PRIORITY_MAX, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, TASK_STATUSES
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task, completion_rate
from models.user import User
from utils.time import utc_now


def _overdue_entries(tasks, now):
    return [
        {
            'id': task.id,
            'title': task.title,
            'due_date': str(task.due_date),
            'days_overdue': (now - task.due_date).days,
        }
        for task in tasks if task.is_overdue(now)
    ]


def summary_report():
    now = utc_now()
    by_status = Task.count_by(Task.status)
    by_priority = Task.count_by(Task.priority)
    overdue = _overdue_entries(Task.list_all(), now)
    recent_since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

    totals_by_user = User.task_counts()
    done_by_user = User.done_task_counts()
    user_productivity = []
    for user in User.list_all():
        total = totals_by_user.get(user.id, 0)
        completed = done_by_user.get(user.id, 0)
        user_productivity.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': completion_rate(completed, total),
        })

    return {
        'generated_at': str(now),
        'overview': {
            'total_tasks': Task.count(),
            'total_users': User.count(),
            'total_categories': Category.count(),
        },
        'tasks_by_status': {status: by_status.get(status, 0) for status in TASK_STATUSES},
        'tasks_by_priority': {label: by_priority.get(priority, 0)
                              for priority, label in PRIORITY_LABELS.items()},
        'overdue': {
            'count': len(overdue),
            'tasks': overdue,
        },
        'recent_activity': {
            'tasks_created_last_7_days': Task.count_created_since(recent_since),
            'tasks_completed_last_7_days': Task.count_done_since(recent_since),
        },
        'user_productivity': user_productivity,
    }


def user_report(user_id):
    user = User.find(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.list_by_user(user_id)
    now = utc_now()
    status_counts = {status: 0 for status in TASK_STATUSES}
    for task in tasks:
        if task.status in status_counts:
            status_counts[task.status] += 1
    total = len(tasks)

    return {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': {
            'total_tasks': total,
            **status_counts,
            'overdue': sum(1 for task in tasks if task.is_overdue(now)),
            'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
            'completion_rate': completion_rate(status_counts['done'], total),
        },
    }
