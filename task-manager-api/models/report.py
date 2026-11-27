"""Regras de agregação dos relatórios e estatísticas de tasks."""
from datetime import timedelta

from config.settings import DONE_STATUS, HIGH_PRIORITY_MAX, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, TASK_STATUSES
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import calculate_percentage
from utils.time import utc_now


def _status_counts():
    counts = Task.count_by(Task.status)
    return {status: counts.get(status, 0) for status in TASK_STATUSES}


def task_stats():
    total = Task.count_all()
    by_status = _status_counts()
    return {
        'total': total,
        **by_status,
        'overdue': len(Task.overdue(utc_now())),
        'completion_rate': calculate_percentage(by_status[DONE_STATUS], total),
    }


def summary():
    now = utc_now()
    priority_counts = Task.count_by(Task.priority)
    overdue_tasks = Task.overdue(now)
    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
    counts_by_user = User.task_counts()

    user_productivity = []
    for user in User.all_ordered():
        total, completed = counts_by_user.get(user.id, (0, 0))
        user_productivity.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': calculate_percentage(completed, total),
        })

    return {
        'generated_at': str(now),
        'overview': {
            'total_tasks': Task.count_all(),
            'total_users': User.count_all(),
            'total_categories': Category.count_all(),
        },
        'tasks_by_status': _status_counts(),
        'tasks_by_priority': {label: priority_counts.get(priority, 0) for priority, label in PRIORITY_LABELS.items()},
        'overdue': {
            'count': len(overdue_tasks),
            'tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'due_date': str(task.due_date),
                    'days_overdue': (now - task.due_date).days,
                }
                for task in overdue_tasks
            ],
        },
        'recent_activity': {
            'tasks_created_last_7_days': Task.count_created_since(since),
            'tasks_completed_last_7_days': Task.count_completed_since(since),
        },
        'user_productivity': user_productivity,
    }


def user_statistics(user):
    tasks = Task.by_user(user.id)
    now = utc_now()
    by_status = {status: 0 for status in TASK_STATUSES}
    for task in tasks:
        if task.status in by_status:
            by_status[task.status] += 1
    total = len(tasks)
    return {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': {
            'total_tasks': total,
            **by_status,
            'overdue': sum(1 for task in tasks if task.is_overdue(now)),
            'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
            'completion_rate': calculate_percentage(by_status[DONE_STATUS], total),
        },
    }
