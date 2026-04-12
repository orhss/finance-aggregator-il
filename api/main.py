"""
FastAPI application factory for the Fin REST API.

Mounts all routers, configures CORS, and provides a health endpoint.

Run with:
    uv run uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    accounts,
    analytics,
    auth_router,
    balances,
    budget,
    categories,
    dividends,
    retirement,
    rules,
    sync,
    tags,
    transactions,
)

app = FastAPI(
    title="Fin REST API",
    description="REST API for the Fin financial data aggregator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ==================== CORS ====================
# Allows the React dev server (localhost:3000) and any production origin.
# Tighten origins in production via the CORS_ORIGINS env var.

import os

_origins_env = os.environ.get("CORS_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Routers ====================

app.include_router(auth_router.router)
app.include_router(accounts.router)
app.include_router(balances.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(budget.router)
app.include_router(tags.router)
app.include_router(categories.router)
app.include_router(rules.router)
app.include_router(sync.router)
app.include_router(retirement.router)
app.include_router(dividends.router)

# ==================== Health ====================

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "fin-api"}


@app.get("/", tags=["system"])
def root():
    return {"message": "Fin API — see /docs for endpoints"}
