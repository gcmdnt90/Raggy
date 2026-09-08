"""The stage console — pre-flight and configuration. Never projected.

Requires authentication (ADMIN_PASSWORD) and binds to loopback only. This is the
only surface allowed to display credentials-adjacent state and trainer material.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()
PAGE = Path(__file__).resolve().parent.parent / "web" / "console" / "index.html"


@router.get("/")
def index() -> FileResponse:
    return FileResponse(PAGE)


# TODO(M4): authentication dependency on every route below.
# TODO(M4): GET  /preflight  -> providers reachable, Ollama up and models pulled,
#   sector chosen, chain files present, recordings present and dated.
# TODO(M1): POST /settings   -> write .env via app.config.save_settings_to_env.
#   Secrets are write-only: never return a stored key to the browser.
