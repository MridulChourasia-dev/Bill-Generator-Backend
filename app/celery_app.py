from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "bill_generator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.reminder_tasks", "app.tasks.report_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Celery Beat scheduled tasks
celery_app.conf.beat_schedule = {
    # Send pending reminders every 5 minutes
    "send-bill-reminders": {
        "task": "app.tasks.reminder_tasks.send_bill_reminders",
        "schedule": crontab(minute="*/5"),
    },
    # Mark overdue bills every hour
    "mark-overdue-bills": {
        "task": "app.tasks.reminder_tasks.mark_overdue_bills",
        "schedule": crontab(minute=0),  # top of every hour
    },
    # Monthly report on the 1st at 8am UTC
    "generate-monthly-report": {
        "task": "app.tasks.report_tasks.generate_monthly_report",
        "schedule": crontab(day_of_month=1, hour=8, minute=0),
    },
    # Clean old sent reminders weekly (Sunday midnight)
    "clean-old-data": {
        "task": "app.tasks.report_tasks.clean_old_data",
        "schedule": crontab(day_of_week=0, hour=0, minute=0),
    },
}
