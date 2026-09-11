"""Banco — one server, two surfaces.

    /          redirects to /console — Banco opens on pre-flight, every time
    /harness   the harness       — projected, no credentials, no trainer material
    /console   the stage console — pre-flight and configuration, authenticated

Both bind to loopback. See CONTEXT.md for the invariants each surface must hold
and docs/adr/0002 for why this is FastAPI and not Streamlit.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.server import console, harness

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Banco", docs_url=None, redoc_url=None)

app.include_router(harness.router)
app.include_router(console.router, prefix="/console")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Banco opens on pre-flight. Every time, not only when unconfigured.

    A machine that worked last week arrives at a client with Ollama not started,
    a key rotated, or the chain files regenerated. The check costs seconds and
    the failure costs a demonstration, so it runs on every launch rather than
    when Banco guesses it is needed.

    This is also why the projected surface moved to `/harness`: `/` now shows
    key fields, and the URL that goes on a projector must be the one that
    cannot.
    """
    return RedirectResponse("/console", status_code=307)


app.mount("/static", StaticFiles(directory=str(WEB_ROOT)), name="static")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe. Used by the agent install contract in AGENTS.md."""
    return {"status": "ok"}


def run(host: str = "127.0.0.1", port: int = 8501) -> None:
    import uvicorn

    uvicorn.run("app.server.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
