"""Optional token-protected local REST API."""
from __future__ import annotations

import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .scanner import scan_workspace

app = FastAPI(
    title="MKAOS Developer API",
    version="0.1.0",
    description="Local-first, read-only workspace scan API. No file writes or remote scanning.",
)

class ScanRequest(BaseModel):
    path: str = Field(default=".", min_length=1, max_length=512)
    max_files: int = Field(default=10_000, ge=1, le=10_000)

def _workspace_root() -> Path:
    return Path(os.environ.get("MKAOS_API_WORKSPACE", ".")).expanduser().resolve()

def _authorize(authorization: str | None) -> None:
    expected = os.environ.get("MKAOS_API_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail="API disabled: set a random MKAOS_API_TOKEN of at least 32 characters.")
    supplied = (authorization or "")
    if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:], expected):
        raise HTTPException(status_code=401, detail="Bearer token required.")

@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mkaos-developer-api", "version": "0.1.0"}

@app.post("/v1/scan")
def scan(request: ScanRequest, authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    root = _workspace_root()
    requested = (root / request.path).resolve()
    if not requested.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Scan path must stay inside MKAOS_API_WORKSPACE.")
    try:
        return scan_workspace(requested, request.max_files)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
