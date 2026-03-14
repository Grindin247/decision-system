from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context
from app.core.db import get_db
from app.schemas.notes import NoteIndexRequest, NoteIndexResponse, NoteSearchRequest, NoteSearchResponse
from app.services.access import require_family, require_family_member
from app.services.notes import search_notes, upsert_note_document

router = APIRouter(prefix="/v1/notes", tags=["notes"])


@router.post("/index", response_model=NoteIndexResponse, status_code=201)
def index_note(
    payload: NoteIndexRequest,
    db: Session = Depends(get_db),
    ctx: AuthContext | None = Depends(get_auth_context),
    x_dev_user: str | None = Header(default=None, alias="X-Dev-User"),
):
    require_family(db, payload.family_id)
    caller = (ctx.email if ctx is not None else (x_dev_user or payload.actor)).strip().lower()
    require_family_member(db, payload.family_id, caller)
    doc = upsert_note_document(db, payload=payload)
    db.commit()
    db.refresh(doc)
    return NoteIndexResponse(
        doc_id=str(doc.doc_id),
        family_id=doc.family_id,
        path=doc.path,
        item_type=doc.item_type,  # type: ignore[arg-type]
        updated_at=doc.updated_at,
    )


@router.post("/search", response_model=NoteSearchResponse)
def note_search(
    payload: NoteSearchRequest,
    db: Session = Depends(get_db),
    ctx: AuthContext | None = Depends(get_auth_context),
    x_dev_user: str | None = Header(default=None, alias="X-Dev-User"),
):
    require_family(db, payload.family_id)
    caller = (ctx.email if ctx is not None else (x_dev_user or payload.actor)).strip().lower()
    require_family_member(db, payload.family_id, caller)
    return NoteSearchResponse(items=search_notes(db, payload=payload))
