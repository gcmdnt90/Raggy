"""Banco — one server, two surfaces.

    /          the harness       — projected, no credentials, no trainer material
    /console   the stage console — pre-flight and configuration, authenticated

Both bind to loopback. See CONTEXT.md for the invariants each surface must hold
and docs/adr/0002 for why this is FastAPI and not Streamlit.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.server import console, harness

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Banco", docs_url=None, redoc_url=None)

app.include_router(harness.router)
app.include_router(console.router, prefix="/console")
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
