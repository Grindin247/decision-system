import os

import httpx

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


@celery_app.task
def sync_keycloak_families():
    base = os.environ.get("DECISION_API_BASE_URL", "http://api:8000/v1").rstrip("/")
    token = os.environ.get("INTERNAL_ADMIN_TOKEN", "")
    if not token:
        return {"job": "keycloak_family_sync", "status": "skipped", "reason": "missing INTERNAL_ADMIN_TOKEN"}

    url = f"{base}/admin/keycloak/sync"
    try:
        resp = httpx.post(url, headers={"X-Internal-Admin-Token": token}, timeout=60.0)
        resp.raise_for_status()
        return {"job": "keycloak_family_sync", "status": "ok", "result": resp.json()}
    except Exception as exc:
        return {"job": "keycloak_family_sync", "status": "error", "error": str(exc)}
