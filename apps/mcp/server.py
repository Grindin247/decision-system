from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

SERVER_NAME = "decision-system-mcp"
API_BASE = os.getenv("DECISION_API_BASE_URL", "http://localhost:8000/v1").rstrip("/")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("DECISION_MCP_HTTP_TIMEOUT_SECONDS", "20"))
AUDIT_LOG_PATH = os.getenv("DECISION_MCP_AUDIT_LOG_PATH", ".decision_mcp_audit.jsonl")

OperationType = Literal[
    "create_family",
    "update_family",
    "delete_family",
    "create_member",
    "update_member",
    "delete_member",
    "create_goal",
    "update_goal",
    "delete_goal",
    "create_decision",
    "update_decision",
    "delete_decision",
    "score_decision",
    "create_roadmap_item",
    "update_roadmap_item",
    "delete_roadmap_item",
    "update_budget_policy",
    "reset_budget_period",
]


class Operation(BaseModel):
    type: OperationType
    payload: dict[str, Any] = Field(default_factory=dict)


class Proposal(BaseModel):
    id: str
    actor_id: str
    actor_name: str | None = None
    rationale: str
    status: Literal["proposed", "confirmed", "committed", "canceled"] = "proposed"
    operations: list[Operation]
    operation_preview: list[str]
    allow_destructive: bool = False
    created_at: str
    confirmed_at: str | None = None
    committed_at: str | None = None
    commit_results: list[dict[str, Any]] = Field(default_factory=list)


class _OperationPlan(BaseModel):
    summary: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    body: dict[str, Any] | None = None
    destructive: bool = False


mcp = FastMCP(SERVER_NAME)
_proposal_lock = threading.Lock()
_proposals: dict[str, Proposal] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_audit_event(event_type: str, payload: dict[str, Any]) -> None:
    row = {"ts": _now_iso(), "event_type": event_type, **payload}
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def _request(
    method: str,
    path: str,
    actor_id: str,
    actor_name: str | None,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "X-Decision-Actor-Id": actor_id,
    }
    if actor_name:
        headers["X-Decision-Actor-Name"] = actor_name

    response = requests.request(
        method=method,
        url=f"{API_BASE}{path}",
        params=query,
        json=body,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code == 204:
        return {"status_code": response.status_code, "body": None}

    try:
        parsed = response.json()
    except requests.JSONDecodeError:
        parsed = {"raw": response.text}

    if not response.ok:
        raise RuntimeError(f"{method} {path} failed ({response.status_code}): {parsed}")
    return {"status_code": response.status_code, "body": parsed}


def _required(payload: dict[str, Any], fields: list[str], op_type: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ValueError(f"{op_type} missing required field(s): {', '.join(missing)}")


def _to_plan(op: Operation) -> _OperationPlan:
    payload = op.payload
    op_type = op.type

    if op_type == "create_family":
        _required(payload, ["name"], op_type)
        return _OperationPlan(summary=f"Create family '{payload['name']}'", method="POST", path="/families", body={"name": payload["name"]})
    if op_type == "update_family":
        _required(payload, ["family_id", "name"], op_type)
        return _OperationPlan(
            summary=f"Update family #{payload['family_id']} name to '{payload['name']}'",
            method="PATCH",
            path=f"/families/{payload['family_id']}",
            body={"name": payload["name"]},
        )
    if op_type == "delete_family":
        _required(payload, ["family_id"], op_type)
        return _OperationPlan(
            summary=f"Delete family #{payload['family_id']}",
            method="DELETE",
            path=f"/families/{payload['family_id']}",
            destructive=True,
        )
    if op_type == "create_member":
        _required(payload, ["family_id", "email", "display_name", "role"], op_type)
        family_id = payload["family_id"]
        return _OperationPlan(
            summary=f"Create member '{payload['display_name']}' in family #{family_id}",
            method="POST",
            path=f"/families/{family_id}/members",
            body={
                "email": payload["email"],
                "display_name": payload["display_name"],
                "role": payload["role"],
            },
        )
    if op_type == "update_member":
        _required(payload, ["family_id", "member_id"], op_type)
        family_id = payload["family_id"]
        member_id = payload["member_id"]
        patch: dict[str, Any] = {}
        if "display_name" in payload:
            patch["display_name"] = payload["display_name"]
        if "role" in payload:
            patch["role"] = payload["role"]
        if not patch:
            raise ValueError("update_member requires display_name and/or role")
        return _OperationPlan(
            summary=f"Update member #{member_id} in family #{family_id}",
            method="PATCH",
            path=f"/families/{family_id}/members/{member_id}",
            body=patch,
        )
    if op_type == "delete_member":
        _required(payload, ["family_id", "member_id"], op_type)
        return _OperationPlan(
            summary=f"Delete member #{payload['member_id']} from family #{payload['family_id']}",
            method="DELETE",
            path=f"/families/{payload['family_id']}/members/{payload['member_id']}",
            destructive=True,
        )
    if op_type == "create_goal":
        _required(payload, ["family_id", "name", "description", "weight"], op_type)
        return _OperationPlan(
            summary=f"Create goal '{payload['name']}' for family #{payload['family_id']}",
            method="POST",
            path="/goals",
            body={
                "family_id": payload["family_id"],
                "name": payload["name"],
                "description": payload["description"],
                "weight": payload["weight"],
                "action_types": payload.get("action_types", []),
                "active": payload.get("active", True),
            },
        )
    if op_type == "update_goal":
        _required(payload, ["goal_id"], op_type)
        patch = {key: payload[key] for key in ["name", "description", "weight", "action_types", "active"] if key in payload}
        if not patch:
            raise ValueError("update_goal requires at least one mutable field")
        return _OperationPlan(summary=f"Update goal #{payload['goal_id']}", method="PATCH", path=f"/goals/{payload['goal_id']}", body=patch)
    if op_type == "delete_goal":
        _required(payload, ["goal_id"], op_type)
        return _OperationPlan(summary=f"Delete goal #{payload['goal_id']}", method="DELETE", path=f"/goals/{payload['goal_id']}", destructive=True)
    if op_type == "create_decision":
        _required(payload, ["family_id", "created_by_member_id", "title", "description"], op_type)
        return _OperationPlan(summary=f"Create decision '{payload['title']}'", method="POST", path="/decisions", body=payload)
    if op_type == "update_decision":
        _required(payload, ["decision_id"], op_type)
        patch = {key: value for key, value in payload.items() if key != "decision_id"}
        if not patch:
            raise ValueError("update_decision requires at least one mutable field")
        return _OperationPlan(
            summary=f"Update decision #{payload['decision_id']}",
            method="PATCH",
            path=f"/decisions/{payload['decision_id']}",
            body=patch,
        )
    if op_type == "delete_decision":
        _required(payload, ["decision_id"], op_type)
        return _OperationPlan(
            summary=f"Delete decision #{payload['decision_id']}",
            method="DELETE",
            path=f"/decisions/{payload['decision_id']}",
            destructive=True,
        )
    if op_type == "score_decision":
        _required(payload, ["decision_id", "goal_scores", "threshold_1_to_5"], op_type)
        decision_id = payload["decision_id"]
        body = {
            "goal_scores": payload["goal_scores"],
            "threshold_1_to_5": payload["threshold_1_to_5"],
            "computed_by": payload.get("computed_by", "human"),
        }
        return _OperationPlan(summary=f"Score decision #{decision_id}", method="POST", path=f"/decisions/{decision_id}/score", body=body)
    if op_type == "create_roadmap_item":
        _required(payload, ["decision_id", "bucket", "status"], op_type)
        body = {
            "decision_id": payload["decision_id"],
            "bucket": payload["bucket"],
            "status": payload["status"],
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "dependencies": payload.get("dependencies", []),
            "use_discretionary_budget": payload.get("use_discretionary_budget", False),
        }
        return _OperationPlan(summary=f"Create roadmap item for decision #{payload['decision_id']}", method="POST", path="/roadmap", body=body)
    if op_type == "update_roadmap_item":
        _required(payload, ["roadmap_id"], op_type)
        roadmap_id = payload["roadmap_id"]
        body = {key: value for key, value in payload.items() if key != "roadmap_id"}
        if not body:
            raise ValueError("update_roadmap_item requires at least one mutable field")
        return _OperationPlan(summary=f"Update roadmap item #{roadmap_id}", method="PATCH", path=f"/roadmap/{roadmap_id}", body=body)
    if op_type == "delete_roadmap_item":
        _required(payload, ["roadmap_id"], op_type)
        return _OperationPlan(summary=f"Delete roadmap item #{payload['roadmap_id']}", method="DELETE", path=f"/roadmap/{payload['roadmap_id']}", destructive=True)
    if op_type == "update_budget_policy":
        _required(payload, ["family_id", "threshold_1_to_5", "period_days", "default_allowance"], op_type)
        family_id = payload["family_id"]
        body = {
            "threshold_1_to_5": payload["threshold_1_to_5"],
            "period_days": payload["period_days"],
            "default_allowance": payload["default_allowance"],
            "member_allowances": payload.get("member_allowances", []),
        }
        return _OperationPlan(summary=f"Update budget policy for family #{family_id}", method="PUT", path=f"/budgets/families/{family_id}/policy", body=body)
    if op_type == "reset_budget_period":
        _required(payload, ["family_id"], op_type)
        return _OperationPlan(summary=f"Reset budget period for family #{payload['family_id']}", method="POST", path=f"/budgets/families/{payload['family_id']}/period/reset")

    raise ValueError(f"unsupported operation type: {op_type}")


def _proposal_output(proposal: Proposal) -> dict[str, Any]:
    return {
        "id": proposal.id,
        "actor_id": proposal.actor_id,
        "actor_name": proposal.actor_name,
        "rationale": proposal.rationale,
        "status": proposal.status,
        "allow_destructive": proposal.allow_destructive,
        "created_at": proposal.created_at,
        "confirmed_at": proposal.confirmed_at,
        "committed_at": proposal.committed_at,
        "operation_preview": proposal.operation_preview,
        "commit_results": proposal.commit_results,
    }


@mcp.tool()
def server_health() -> dict[str, Any]:
    """Verify MCP server and Decision API connectivity."""
    result = _request("GET", "/health", actor_id="mcp-system", actor_name=SERVER_NAME)
    return {"mcp_server": SERVER_NAME, "api_base": API_BASE, "api_health": result["body"]}


@mcp.tool()
def list_families() -> dict[str, Any]:
    """Read families."""
    return _request("GET", "/families", actor_id="read-only", actor_name=SERVER_NAME)["body"]


@mcp.tool()
def list_family_members(family_id: int) -> dict[str, Any]:
    """Read members for a family."""
    return _request("GET", f"/families/{family_id}/members", actor_id="read-only", actor_name=SERVER_NAME)["body"]


@mcp.tool()
def list_goals(family_id: int, active_only: bool = False) -> dict[str, Any]:
    """Read goals for a family."""
    return _request(
        "GET",
        "/goals",
        actor_id="read-only",
        actor_name=SERVER_NAME,
        query={"family_id": family_id, "active_only": str(active_only).lower()},
    )["body"]


@mcp.tool()
def list_decisions(family_id: int, include_scores: bool = True) -> dict[str, Any]:
    """Read decisions for a family."""
    return _request(
        "GET",
        "/decisions",
        actor_id="read-only",
        actor_name=SERVER_NAME,
        query={"family_id": family_id, "include_scores": str(include_scores).lower()},
    )["body"]


@mcp.tool()
def list_roadmap_items(family_id: int) -> dict[str, Any]:
    """Read roadmap items for a family."""
    return _request("GET", "/roadmap", actor_id="read-only", actor_name=SERVER_NAME, query={"family_id": family_id})["body"]


@mcp.tool()
def get_budget_summary(family_id: int) -> dict[str, Any]:
    """Read discretionary budget summary for a family."""
    return _request("GET", f"/budgets/families/{family_id}", actor_id="read-only", actor_name=SERVER_NAME)["body"]


@mcp.tool()
def propose_changes(
    actor_id: str,
    rationale: str,
    operations: list[Operation],
    actor_name: str | None = None,
    allow_destructive: bool = False,
) -> dict[str, Any]:
    """Stage mutable changes. Nothing is persisted until confirm + commit."""
    if not operations:
        raise ValueError("operations must not be empty")

    plans = [_to_plan(op) for op in operations]
    destructive = any(plan.destructive for plan in plans)
    if destructive and not allow_destructive:
        raise ValueError("proposal includes destructive operation(s). Re-run with allow_destructive=true after explicit user confirmation.")

    proposal = Proposal(
        id=str(uuid.uuid4()),
        actor_id=actor_id,
        actor_name=actor_name,
        rationale=rationale,
        operations=operations,
        operation_preview=[plan.summary for plan in plans],
        allow_destructive=allow_destructive,
        created_at=_now_iso(),
    )

    with _proposal_lock:
        _proposals[proposal.id] = proposal
    _append_audit_event("proposal_created", _proposal_output(proposal))
    return _proposal_output(proposal)


@mcp.tool()
def get_proposal(proposal_id: str) -> dict[str, Any]:
    """Fetch current proposal state."""
    with _proposal_lock:
        proposal = _proposals.get(proposal_id)
    if proposal is None:
        raise ValueError(f"proposal not found: {proposal_id}")
    return _proposal_output(proposal)


@mcp.tool()
def confirm_proposal(proposal_id: str, actor_id: str, confirmation_note: str) -> dict[str, Any]:
    """Confirm a staged proposal before commit."""
    with _proposal_lock:
        proposal = _proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"proposal not found: {proposal_id}")
        if proposal.status != "proposed":
            raise ValueError(f"proposal status is {proposal.status}; only proposed items can be confirmed")
        if proposal.actor_id != actor_id:
            raise ValueError("actor_id must match proposal owner")
        proposal.status = "confirmed"
        proposal.confirmed_at = _now_iso()
        _proposals[proposal_id] = proposal

    _append_audit_event(
        "proposal_confirmed",
        {
            "proposal_id": proposal_id,
            "actor_id": actor_id,
            "confirmation_note": confirmation_note,
            "confirmed_at": proposal.confirmed_at,
        },
    )
    return _proposal_output(proposal)


@mcp.tool()
def cancel_proposal(proposal_id: str, actor_id: str, reason: str) -> dict[str, Any]:
    """Cancel a staged proposal."""
    with _proposal_lock:
        proposal = _proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"proposal not found: {proposal_id}")
        if proposal.status in {"committed", "canceled"}:
            raise ValueError(f"proposal already {proposal.status}")
        if proposal.actor_id != actor_id:
            raise ValueError("actor_id must match proposal owner")
        proposal.status = "canceled"
        _proposals[proposal_id] = proposal

    _append_audit_event("proposal_canceled", {"proposal_id": proposal_id, "actor_id": actor_id, "reason": reason})
    return _proposal_output(proposal)


@mcp.tool()
def commit_proposal(proposal_id: str, actor_id: str) -> dict[str, Any]:
    """Persist a confirmed proposal as atomic, ordered API calls."""
    with _proposal_lock:
        proposal = _proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"proposal not found: {proposal_id}")
        if proposal.status != "confirmed":
            raise ValueError(f"proposal status is {proposal.status}; only confirmed items can be committed")
        if proposal.actor_id != actor_id:
            raise ValueError("actor_id must match proposal owner")

    plans = [_to_plan(op) for op in proposal.operations]
    results: list[dict[str, Any]] = []
    for index, plan in enumerate(plans, start=1):
        result = _request(plan.method, plan.path, actor_id=proposal.actor_id, actor_name=proposal.actor_name, body=plan.body)
        results.append(
            {
                "index": index,
                "summary": plan.summary,
                "request": {"method": plan.method, "path": plan.path, "body": plan.body},
                "response": result,
            }
        )

    with _proposal_lock:
        proposal = _proposals[proposal_id]
        proposal.status = "committed"
        proposal.committed_at = _now_iso()
        proposal.commit_results = results
        _proposals[proposal_id] = proposal

    _append_audit_event("proposal_committed", _proposal_output(proposal))
    return _proposal_output(proposal)


if __name__ == "__main__":
    mcp.run()
