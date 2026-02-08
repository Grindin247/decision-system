from celery import Celery

celery_app = Celery(
    "decision_worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery_app.conf.beat_schedule = {
    "daily-due-summary": {
        "task": "worker.tasks.send_due_soon_summary",
        "schedule": 86400.0,
    },
    "weekly-roadmap-nudges": {
        "task": "worker.tasks.send_roadmap_nudges",
        "schedule": 604800.0,
    },
    "quarterly-rollover-check": {
        "task": "worker.tasks.run_period_rollover",
        "schedule": 86400.0,
    },
}
celery_app.conf.timezone = "UTC"
