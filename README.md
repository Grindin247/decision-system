# Family Decision Making System

Monorepo starter for a spec-first Family Decision Making System.

## Stack
- API: FastAPI + SQLAlchemy + Alembic + Postgres
- Web: Next.js 14 (App Router)
- Worker: Celery + Redis
- Infra: Docker Compose + Nginx reverse proxy

## Keycloak SSO + Family Sync
When running inside Family-Cloud, the decision system is intended to sit behind Traefik Forward Auth (Keycloak OIDC).

Additionally, Keycloak groups ending with `_family` are mirrored into the decision system as Families, with group members
synced into FamilyMembers on a schedule (Celery beat).

## Quick start
1. Copy environment template:
   - `Copy-Item .env.example .env`
2. Start stack:
   - `docker compose --profile dev up --build`
3. API docs:
   - `http://localhost:8000/docs`
4. Web UI:
   - `http://localhost:3000`

## Repo layout
- `apps/api`: backend API and data model
- `apps/web`: frontend shell
- `apps/worker`: scheduled jobs and async tasks
- `apps/mcp`: MCP server for AI agent tool access
- `docs/specs`: product, API, AI, UX, security specifications
- `docs/runbooks`: backup/restore and operations docs
- `infra`: compose, reverse proxy, scripts

## MCP server
The repo includes an MCP server (`apps/mcp`) that exposes safe tools for managing:
- families and members
- goals
- decisions and scoring
- roadmap scheduling
- discretionary budget policy and periods

Mutable operations require `propose_changes -> confirm_proposal -> commit_proposal` before data is persisted.
See `apps/mcp/README.md` for setup and agent registration.

## Current scope
This scaffold sets up the project skeleton and contracts needed to start implementing all requested workstreams.
