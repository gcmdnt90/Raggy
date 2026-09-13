"""Banco — one server, two surfaces.

    /          redirects to /console — Banco opens on pre-flight, every time
    /harness   the harness       — projected, no credentials, no trainer material
    /console   the stage console — pre-flight and configuration, authenticated

Both bind to loopback. See CONTEXT.md for the invariants each surface must hold
and docs/adr/0002 for why this is FastAPI and not Streamlit.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import LOG_DIR
from app.server import console, harness
from app.utils.logging_config import cleanup_old_logs, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging when the server starts, and bound what it keeps.

    Nothing called `setup_logging`, so Banco ran with no log file at all: a
    provider failure left no record anywhere on disk, and the
    credential-redacting filter that `setup_logging` installs was never
    attached. On startup rather than at import, so merely importing the app in
    a test does not write to `logs/`.

    The retention sweep runs here too: `TimedRotatingFileHandler.backupCount`
    only prunes what it rotated within one process, and Banco is started fresh
    for each lesson rather than left running.
    """
    setup_logging()
    cleanup_old_logs(LOG_DIR)
    yield


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Banco", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware("http")
async def _revalidate_surfaces(request: Request, call_next):
    """Make the browser re-check the page and its assets on every load.

    Neither `StaticFiles` nor `FileResponse` sends `Cache-Control`, so a
    browser is free to apply heuristic freshness and reuse a cached stylesheet
    without asking. Banco's CSS is edited between lessons and the server is
    restarted rather than versioned, which is exactly the case where that
    guess is wrong: the trainer reloads, sees the previous design, and has no
    reason to suspect the browser.

    `no-cache` is revalidate-every-time, not don't-store: the ETag still
    answers 304 when nothing changed, so this costs a conditional request.
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path in ("/harness", "/console", "/console/"):
        response.headers["Cache-Control"] = "no-cache"
    return response

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
