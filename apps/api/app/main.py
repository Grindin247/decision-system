from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin_keycloak, audit, auth, budgets, decisions, families, goals, health, roadmap

app = FastAPI(
    title="Family Decision System API",
    version="1.0.0",
    description="API for decision lifecycle, scoring, budgeting, and roadmap management.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(families.router)
app.include_router(goals.router)
app.include_router(decisions.router)
app.include_router(roadmap.router)
app.include_router(budgets.router)
app.include_router(audit.router)
app.include_router(admin_keycloak.router)
