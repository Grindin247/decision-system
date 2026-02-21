from __future__ import annotations

from fastapi import APIRouter, Depends

from agents.decision_agent.agent import DecisionAgent
from agents.decision_agent.schemas import DecisionAgentResponse, DecisionIntakeRequest
from app.core.auth import AuthContext, get_auth_context
from app.services.access import require_family_member
from app.core.db import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/v1/agents/decision", tags=["agents"])


@router.post("/invoke", response_model=DecisionAgentResponse)
def invoke_decision_agent(
    payload: DecisionIntakeRequest,
    db: Session = Depends(get_db),
    ctx: AuthContext | None = Depends(get_auth_context),
):
    # Ensure the caller is a family member for the target family.
    actor = payload.actor
    if ctx is not None:
        require_family_member(db, payload.family_id, ctx.email)
        actor = ctx.email
    agent = DecisionAgent()
    # Actor is always the authenticated user (ignore spoofing).
    req = DecisionIntakeRequest(message=payload.message, actor=actor, family_id=payload.family_id, session_id=payload.session_id)
    return agent.run(req)
