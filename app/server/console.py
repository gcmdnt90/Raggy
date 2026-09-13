"""The stage console — pre-flight and configuration. Never projected.

Binds to loopback and is the only surface allowed to touch credentials. Keys are
**write-only**: they can be set here and their presence reported, but no route
ever returns one, not even masked. A masked key on a screen that gets projected
by accident is still part of a real key.

Authentication bootstraps rather than blocks. On a fresh install there is no
password to check, so the console is reachable and says loudly that it is
unprotected; once a password is set it is required. Refusing to serve the setup
screen until someone hand-edits `.env` would make the first-run experience
"edit a file before you can use the thing that edits files".
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Annotated

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, field_validator

from app.config import get_settings, save_settings_to_env
from app.i18n import DEFAULT_LANGUAGE, normalize, t
from app.server import preflight, runner, sources
from app.utils.redact import redact

router = APIRouter()
PAGE = Path(__file__).resolve().parent.parent / "web" / "console" / "index.html"

_basic = HTTPBasic(auto_error=False)

#: Providers whose keys this console may write. Anything else is a typo.
WRITABLE_KEYS = set(sources.API_ORDER)


def require_console(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)] = None,
    lang: str = DEFAULT_LANGUAGE,
):
    """Gate the console once a password exists; stay open until one does.

    The comparison is constant-time. The username is not checked: there is one
    console and one operator, and inventing a username would only add something
    else to forget before a lesson.

    `lang` is declared here rather than on each route so that every console
    endpoint accepts it and the 401 itself is written in the language the
    browser asked for. It is normalized, never trusted: an unknown code means
    Italian, not an error.
    """
    lang = normalize(lang)
    settings = get_settings()
    check = preflight.admin_password(settings)
    if not check.ok:
        return {"authenticated": False, "unprotected": True, "lang": lang}

    # Compared as bytes, not as str: `compare_digest` raises TypeError on a
    # string containing non-ASCII, and a trainer who chose an accented password
    # would meet a 500 instead of a login prompt — locked out of the console by
    # the act of protecting it.
    expected = settings.admin_password.encode("utf-8")
    supplied = (credentials.password if credentials else "").encode("utf-8")
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=t("console.auth.required", lang),
            headers={"WWW-Authenticate": 'Basic realm="Banco stage console"'},
        )
    return {"authenticated": True, "unprotected": False, "lang": lang}


#: Every console route depends on this. Written as an Annotated alias rather
#: than a default argument so the dependency is part of the type, not a call
#: evaluated once at import.
ConsoleAuth = Annotated[dict, Depends(require_console)]


class KeyUpdate(BaseModel):
    """Keys to store. Empty values are ignored, never written as blanks.

    Sending an empty string is how a browser form says "I did not retype the key
    I cannot see", not "delete it". Deletion is a separate, explicit action.
    """

    anthropic_api_key: str = Field(default="", max_length=512)
    openai_api_key: str = Field(default="", max_length=512)
    google_api_key: str = Field(default="", max_length=512)
    ollama_base_url: str = Field(default="", max_length=512)
    admin_password: str = Field(default="", max_length=512)

    @field_validator("*")
    @classmethod
    def _no_control_characters(cls, value: str) -> str:
        """Refuse a value that could write a second line into `.env`.

        `.env` is line-oriented and `save_settings_to_env` writes `key=value`
        verbatim, so a newline in a pasted value silently defines another
        variable — including one this model does not list, such as a different
        provider's key. Rejected here rather than repaired, because a
        credential that needed repairing is a credential that was mistyped.
        """
        if any(char in value for char in "\r\n\x00"):
            raise ValueError("value must not contain line breaks or null bytes")
        return value


class PullRequest(BaseModel):
    model: str = Field(min_length=1, max_length=128)


@router.get("/")
def index() -> FileResponse:
    """The console page itself is unauthenticated; every route it calls is not.

    Serving the shell without a password lets the browser show the prompt in
    context rather than as a bare dialog on a blank page.
    """
    return FileResponse(PAGE)


@router.get("/preflight")
def get_preflight(
    auth: ConsoleAuth,
    sector: str = "numismatics",
    probe: bool = True,
) -> dict:
    """Everything the trainer must know before starting. No credential values."""
    report = preflight.report(
        get_settings(), sector, probe_ollama=probe, lang=auth["lang"]
    )
    report["authenticated"] = auth["authenticated"]
    report["lang"] = auth["lang"]
    return report


@router.post("/keys")
def set_keys(update: KeyUpdate, auth: ConsoleAuth) -> dict:
    """Store keys in `.env`. Write-only: the response says what changed, not what.

    A key that fails to validate is still stored. Banco cannot tell a wrong key
    from a rate-limited one without spending a call, and refusing to save would
    lose what the trainer just typed.
    """
    updates: dict[str, str] = {}

    for field in WRITABLE_KEYS:
        name = f"{field}_api_key"
        value = getattr(update, name, "").strip()
        if value:
            updates[name] = value

    if update.ollama_base_url.strip():
        # Validated here rather than at load, so a bad URL is rejected while the
        # trainer is looking at the field they typed it into.
        from app.utils.network import normalize_ollama_base_url

        try:
            updates["ollama_base_url"] = normalize_ollama_base_url(
                update.ollama_base_url, lang=auth["lang"]
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    if update.admin_password.strip():
        updates["admin_password"] = update.admin_password.strip()

    if not updates:
        return {"saved": [], "detail": t("console.keys.nothing", auth["lang"])}

    # `get_settings()` builds a fresh Settings each call and re-reads .env, so
    # the next request sees the new value with nothing to invalidate.
    save_settings_to_env(updates)

    # Names only. The values have gone to .env and nowhere else.
    return {
        "saved": sorted(updates),
        "detail": t("console.keys.saved", auth["lang"], count=len(updates)),
    }


@router.post("/keys/clear")
def clear_key(update: KeyUpdate, auth: ConsoleAuth) -> dict:
    """Explicitly blank a stored key. Separate from saving, so it cannot happen
    by submitting a form with an empty field."""
    cleared = [
        f"{p}_api_key"
        for p in WRITABLE_KEYS
        if getattr(update, f"{p}_api_key", "") == "CLEAR"
    ]
    if not cleared:
        return {"cleared": [], "detail": t("console.keys.clear_hint", auth["lang"])}
    save_settings_to_env(dict.fromkeys(cleared, ""))
    return {
        "cleared": cleared,
        "detail": t("console.keys.cleared", auth["lang"], count=len(cleared)),
    }


@router.post("/check")
def run_check(auth: ConsoleAuth, sector: str = "numismatics") -> dict:
    """The full check, including a real call to every configured source.

    Separate from `GET /preflight` because it spends a call per source and takes
    as long as the slowest provider. Pre-flight renders instantly; this is the
    button a trainer presses before a lesson.
    """
    settings = get_settings()
    report = preflight.report(settings, sector, probe_ollama=True, lang=auth["lang"])
    report["live"] = preflight.live_checks(settings, lang=auth["lang"])
    report["all_sources_live"] = bool(report["live"]) and all(
        c["ok"] for c in report["live"].values()
    )
    return report


@router.get("/ollama")
def get_ollama(auth: ConsoleAuth) -> dict:
    """Ollama state: installed, running, models present, and what suits this box."""
    return preflight.ollama(get_settings())


@router.post("/ollama/pull")
def pull_model(request: PullRequest, auth: ConsoleAuth) -> StreamingResponse:
    """Pull a model, streaming Ollama's own progress.

    Goes through Ollama's HTTP API rather than the `ollama` CLI: the server is
    what Banco actually talks to, so if the API answers the pull will be usable,
    whereas the CLI can be absent from PATH while the server runs perfectly well.
    """
    settings = get_settings()
    base_url = settings.ollama_base_url

    def stream():
        try:
            with requests.post(
                f"{base_url}/api/pull",
                json={"model": request.model, "stream": True},
                stream=True,
                timeout=(10, 3600),
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    yield f"data: {line}\n\n"
            yield 'event: done\ndata: {"ok": true}\n\n'
        except requests.RequestException as exc:
            # json.dumps, not an f-string: the message can contain quotes or a
            # newline, either of which would break the SSE frame and leave the
            # console parsing a truncated line as the error.
            payload = json.dumps({"error": redact(f"{type(exc).__name__}: {exc}")})
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/transcripts/reset")
def reset_transcripts(auth: ConsoleAuth) -> dict[str, str]:
    """Forget stored exchanges, so a rehearsal does not leak into the lesson."""
    runner.reset_transcripts()
    return {"status": "cleared"}
