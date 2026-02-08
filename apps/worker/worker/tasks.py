from worker.celery_app import celery_app


@celery_app.task
def send_due_soon_summary():
    return {"job": "due_soon_summary", "status": "stub"}


@celery_app.task
def send_roadmap_nudges():
    return {"job": "roadmap_nudges", "status": "stub"}


@celery_app.task
def run_period_rollover():
    return {"job": "period_rollover", "status": "stub"}
