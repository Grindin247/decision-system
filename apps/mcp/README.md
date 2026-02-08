# Decision System MCP Server

This MCP server exposes safe, structured tools for families, members, goals, decisions, scoring, roadmap, and budget operations.

## Safety Model

All mutable operations must follow:

1. `propose_changes`
2. `confirm_proposal`
3. `commit_proposal`

Nothing is persisted until `commit_proposal`.

Destructive operations (`delete_*`) are blocked unless `allow_destructive=true` is set during proposal.

## Attribution

Every proposal/confirmation/commit includes:

- `actor_id` (required)
- `actor_name` (optional)

These are:

- Logged to `DECISION_MCP_AUDIT_LOG_PATH` (JSONL).
- Sent to API as `X-Decision-Actor-Id` and `X-Decision-Actor-Name` headers.

## Run (local)

```bash
cd apps/mcp
pip install -r requirements.txt
DECISION_API_BASE_URL=http://localhost:8000/v1 python server.py
```

## Run (docker compose)

```bash
docker compose --profile agent up -d mcp
```

## Example Agent Config (stdio)

```json
{
  "mcpServers": {
    "decision-system": {
      "command": "python",
      "args": ["apps/mcp/server.py"],
      "env": {
        "DECISION_API_BASE_URL": "http://localhost:8000/v1",
        "DECISION_MCP_AUDIT_LOG_PATH": ".decision_mcp_audit.jsonl"
      }
    }
  }
}
```

## Read Tools

- `server_health`
- `list_families`
- `list_family_members`
- `list_goals`
- `list_decisions`
- `list_roadmap_items`
- `get_budget_summary`

## Workflow Tools

- `propose_changes`
- `get_proposal`
- `confirm_proposal`
- `cancel_proposal`
- `commit_proposal`

