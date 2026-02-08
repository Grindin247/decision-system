# Family Decision Making System

Monorepo starter for a spec-first Family Decision Making System.

## Stack
- API: FastAPI + SQLAlchemy + Alembic + Postgres
- Web: Next.js 14 (App Router)
- Worker: Celery + Redis
- Infra: Docker Compose + Nginx reverse proxy

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
- `docs/specs`: product, API, AI, UX, security specifications
- `docs/runbooks`: backup/restore and operations docs
- `infra`: compose, reverse proxy, scripts

## Current scope
This scaffold sets up the project skeleton and contracts needed to start implementing all requested workstreams.
