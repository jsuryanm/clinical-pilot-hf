"""FastAPI entrypoint.

Run locally: `make api`
Health:      http://localhost:8000/health
OpenAPI:     http://localhost:8000/docs
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.audit import AuditMiddleware
from app.api.routers import appointment, clerical, discharge, documentation, handover, roster

log = structlog.get_logger(__name__)

app = FastAPI(
    title="CliniqAI Backend",
    description="Clinical operations AI for Indian hospitals — multi-agent backend.",
    version="0.0.1",
)

# CORS — HF Space lives on a different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

# Per-person routers
app.include_router(documentation.router, prefix="/documentation", tags=["documentation"])
app.include_router(appointment.router, prefix="/appointment", tags=["appointment"])
app.include_router(clerical.router, prefix="/clerical", tags=["clerical"])
app.include_router(discharge.router, prefix="/discharge", tags=["discharge"])
app.include_router(roster.router, prefix="/roster", tags=["roster"])
app.include_router(handover.router, prefix="/handover", tags=["handover"])


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "env": os.getenv("CLINIQ_ENV", "dev"),
        "service": "cliniqai-backend",
    }


@app.post("/orchestrate")
def orchestrate(payload: dict[str, str]) -> dict[str, Any]:
    """One-shot orchestrator endpoint — used by the Gradio UI."""
    from app.orchestrator import run  # local import to keep cold-start fast

    utterance = payload.get("utterance", "")
    session_id = payload.get("session_id", "demo")
    out = run(utterance, session_id=session_id)
    # Pydantic models -> JSON-friendly
    serial: dict[str, Any] = {}
    for k, v in out.items():
        if v is None:
            serial[k] = None
        elif hasattr(v, "model_dump"):
            serial[k] = v.model_dump(mode="json")
        else:
            serial[k] = str(v)
    return serial
