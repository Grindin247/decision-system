from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.services.access import require_family
from app.services.purge import purge_family

router = APIRouter(prefix="/v1/admin/families", tags=["admin"])


@router.delete("/{family_id}", status_code=204)
def delete_family_admin(
    family_id: int,
    db: Session = Depends(get_db),
    x_internal_admin_token: str | None = Header(default=None, alias="X-Internal-Admin-Token"),
):
    if not x_internal_admin_token or x_internal_admin_token != settings.internal_admin_token:
        raise HTTPException(status_code=401, detail="invalid internal admin token")

    family = require_family(db, family_id)
    purge_family(db, family.id)
    db.commit()

