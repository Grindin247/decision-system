import os
from datetime import date, datetime, timezone

import httpx

from worker.celery_app import celery_app
from agents.common.events.publisher import EventPublisher
from agents.common.events.subjects import Subjects


@celery_app.task
def send_due_soon_summary():
    base = os.environ.get("DECISION_API_BASE_URL", "http://api:8000/v1").rstrip("/")
    token = os.environ.get("INTERNAL_ADMIN_TOKEN", "")
    if not token:
        return {"job": "due_soon_summary", "status": "skipped", "reason": "missing INTERNAL_ADMIN_TOKEN"}

    days_list = [7, 3, 1]
    today = datetime.now(timezone.utc).date()
    pub = EventPublisher()
    emitted = 0

    try:
        fams = httpx.get(f"{base}/admin/families", headers={"X-Internal-Admin-Token": token}, timeout=30.0).json()["items"]
    except Exception as exc:
        return {"job": "due_soon_summary", "status": "error", "error": f"list families failed: {exc}"}

    for fam in fams:
        family_id = int(fam["id"])
        try:
            items = httpx.get(
                f"{base}/admin/families/{family_id}/roadmap_items",
                headers={"X-Internal-Admin-Token": token},
                timeout=30.0,
            ).json()["items"]
        except Exception:
            continue

        for it in items:
            end = it.get("end_date") or it.get("start_date")
            if not end:
                continue
            try:
                due = date.fromisoformat(end)
            except Exception:
                continue
            delta = (due - today).days
            if delta in days_list:
                try:
                    pub.publish_sync(
                        Subjects.ROADMAP_ITEM_DUE_SOON,
                        {
                            "roadmap_item_id": int(it["id"]),
                            "decision_id": int(it["decision_id"]),
                            "due_date": due.isoformat(),
                            "days_until": delta,
                            "status": it.get("status"),
                        },
                        actor="system-reminder",
                        family_id=family_id,
                        source="decision-worker.reminders",
                    )
                    emitted += 1
                except Exception:
                    pass

    return {"job": "due_soon_summary", "status": "ok", "events_emitted": emitted}


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
