"""The stage console: what it may hold, what it must never return.

The console is the only surface allowed near a credential, so most of what is
checked here is a negative — that a key goes in and never comes back out.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.server import console, harness, preflight


class Settings:
    anthropic_api_key = ""
    openai_api_key = ""
    google_api_key = ""
    ollama_base_url = "http://127.0.0.1:11434"
    llm_provider = "ollama"
    llm_model = "qwen3:8b"
    admin_password = "changeme"
    max_tokens = 64


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def client(monkeypatch, settings):
    monkeypatch.setattr(console, "get_settings", lambda: settings)
    monkeypatch.setattr(harness, "get_settings", lambda: settings)
    monkeypatch.setattr(preflight.sources, "ollama_source", lambda s, check=True: None)

    app = FastAPI()
    app.include_router(harness.router)
    app.include_router(console.router, prefix="/console")
    return TestClient(app)


@pytest.fixture
def saved(monkeypatch):
    """Capture what would be written to .env instead of writing it."""
    store: dict = {}
    monkeypatch.setattr(console, "save_settings_to_env", store.update)
    return store


# ── the first screen ────────────────────────────────────────────────────────

def test_root_always_opens_pre_flight():
    """Every launch, not only an unconfigured one.

    Tested against the real application rather than the router, because the
    redirect is what a trainer's browser meets first and it lives in main.py.
    """
    from app.server.main import app as real_app

    with TestClient(real_app) as real:
        res = real.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "/console"


def test_the_harness_has_its_own_route(client):
    """`/harness` is the URL that goes on a projector; `/` shows key fields."""
    assert client.get("/harness").status_code == 200


def test_the_harness_route_does_not_depend_on_configuration(client, settings):
    """Pre-flight is where readiness is decided, not the harness route."""
    settings.anthropic_api_key = ""
    assert client.get("/harness").status_code == 200


# ── bootstrap authentication ────────────────────────────────────────────────

def test_console_is_open_while_no_password_is_set(client):
    res = client.get("/console/preflight")
    assert res.status_code == 200
    assert res.json()["unprotected"] is True


def test_console_says_loudly_that_it_is_unprotected(client):
    """And says it in Italian, which is what a console with no `lang` speaks."""
    check = client.get("/console/preflight").json()["checks"]["admin_password"]
    assert check["ok"] is False
    assert "non ha una password" in check["detail"].lower()


def test_pre_flight_answers_in_the_language_the_browser_asked_for(client):
    """`lang` travels on the request; there is no server-side language."""
    english = client.get("/console/preflight?lang=en").json()["checks"]
    italian = client.get("/console/preflight?lang=it").json()["checks"]

    assert "no password" in english["admin_password"]["detail"].lower()
    assert "non ha una password" in italian["admin_password"]["detail"].lower()
    # Two consecutive requests in two languages must not have influenced each
    # other: this is the regression the old process-wide `_ui_language` caused.
    assert english["chain"]["detail"] != italian["chain"]["detail"]


def test_an_unknown_language_falls_back_to_italian_rather_than_failing(client):
    res = client.get("/console/preflight?lang=klingon")
    assert res.status_code == 200
    assert "non ha una password" in res.json()["checks"]["admin_password"]["detail"].lower()


def test_the_shipped_placeholder_does_not_count_as_a_password(client, settings):
    settings.admin_password = preflight.DEFAULT_ADMIN_PASSWORD
    assert client.get("/console/preflight").json()["unprotected"] is True


def test_console_is_gated_once_a_password_is_set(client, settings):
    settings.admin_password = "a real one"
    assert client.get("/console/preflight").status_code == 401
    ok = client.get("/console/preflight", auth=("trainer", "a real one"))
    assert ok.status_code == 200
    assert ok.json()["unprotected"] is False


def test_a_wrong_password_is_refused(client, settings):
    settings.admin_password = "a real one"
    assert client.get("/console/preflight", auth=("trainer", "nearly")).status_code == 401


# ── keys are write-only ─────────────────────────────────────────────────────

def test_preflight_reports_key_presence_and_never_the_key(client, settings):
    settings.anthropic_api_key = "sk-secret-value"
    body = client.get("/console/preflight")
    assert body.json()["api_keys"] == {"anthropic": True, "openai": False, "google": False}
    assert "sk-secret-value" not in body.text


def test_saving_a_key_returns_only_its_name(client, saved):
    res = client.post("/console/keys", json={"anthropic_api_key": "sk-secret-value"})
    assert res.status_code == 200
    assert res.json()["saved"] == ["anthropic_api_key"]
    assert "sk-secret-value" not in res.text
    assert saved["anthropic_api_key"] == "sk-secret-value"


def test_a_blank_field_keeps_the_stored_key(client, saved):
    """An empty box means 'I did not retype what I cannot see', not 'delete it'."""
    client.post("/console/keys", json={"anthropic_api_key": "", "openai_api_key": "sk-b"})
    assert "anthropic_api_key" not in saved
    assert saved["openai_api_key"] == "sk-b"


def test_clearing_a_key_needs_an_explicit_word(client, saved):
    blank = client.post("/console/keys/clear", json={"anthropic_api_key": ""})
    assert blank.json()["cleared"] == []
    assert saved == {}
    res = client.post("/console/keys/clear", json={"anthropic_api_key": "CLEAR"})
    assert res.json()["cleared"] == ["anthropic_api_key"]
    assert saved["anthropic_api_key"] == ""


def test_a_password_can_be_set_through_the_console(client, saved):
    client.post("/console/keys", json={"admin_password": "chosen"})
    assert saved["admin_password"] == "chosen"


# ── the Ollama address is validated where it is typed ───────────────────────

def test_a_remote_ollama_address_is_refused_with_a_reason(client, saved):
    res = client.post("/console/keys", json={"ollama_base_url": "http://192.168.1.10:11434"})
    assert res.status_code == 422
    assert "loopback" in res.json()["detail"].lower()
    assert saved == {}


def test_a_loopback_address_is_normalised_and_stored(client, saved):
    res = client.post("/console/keys", json={"ollama_base_url": "http://127.0.0.1:11434/"})
    assert res.status_code == 200
    assert saved["ollama_base_url"] == "http://127.0.0.1:11434"


# ── pre-flight content ──────────────────────────────────────────────────────

def test_preflight_reports_the_chain_files(client):
    chain = client.get("/console/preflight?sector=numismatics").json()["checks"]["chain"]
    assert chain["ok"] is True, chain["detail"]


def test_preflight_flags_a_missing_recording_without_calling_it_a_failure(client):
    rec = client.get("/console/preflight").json()["checks"]["recordings"]
    assert rec["ok"] is False
    assert "degrade" in rec["detail"].lower() or "replay" in rec["detail"].lower()


def test_preflight_says_it_is_not_ready_with_no_source_at_all(client):
    data = client.get("/console/preflight").json()
    assert data["profile"] == "unconfigured"
    assert data["ready_to_run"] is False


def test_preflight_becomes_ready_once_a_key_is_stored(client, settings):
    settings.anthropic_api_key = "sk-test"
    data = client.get("/console/preflight").json()
    assert data["ready_to_run"] is True
    assert data["profile"] == "take-home"


# ── the live check ──────────────────────────────────────────────────────────

def test_live_check_calls_each_configured_source(client, settings, monkeypatch):
    """The only check that tells a working key from a merely stored one."""
    settings.anthropic_api_key = "sk-test"
    called = []

    def fake(role, source, s, **_):
        called.append((role, source.provider))
        return preflight.Check(ok=True, detail=f"{role}: {source.provider} answered.")

    monkeypatch.setattr(preflight, "check_source", fake)
    data = client.post("/console/check").json()

    assert called == [("primary", "anthropic")]
    assert data["all_sources_live"] is True
    assert data["live"]["primary"]["ok"] is True


def test_live_check_reports_a_key_that_does_not_work(client, settings, monkeypatch):
    settings.anthropic_api_key = "sk-wrong"
    monkeypatch.setattr(
        preflight, "check_source",
        lambda role, source, s, **_: preflight.Check(
            ok=False, detail="primary: anthropic refused", action="stored but not working"
        ),
    )
    data = client.post("/console/check").json()
    assert data["all_sources_live"] is False
    assert "refused" in data["live"]["primary"]["detail"]


def test_live_check_never_returns_the_key_it_used(client, settings, monkeypatch):
    settings.anthropic_api_key = "sk-secret-value"
    monkeypatch.setattr(
        preflight, "check_source",
        lambda role, source, s, **_: preflight.Check(ok=True, detail="fine"),
    )
    assert "sk-secret-value" not in client.post("/console/check").text


def test_live_check_is_empty_with_no_source_at_all(client):
    data = client.post("/console/check").json()
    assert data["live"] == {}
    assert data["all_sources_live"] is False


def test_live_check_covers_a_configured_key_that_fills_no_pane(client, settings, monkeypatch):
    """Two API roles, three possible keys — the third was never called.

    A key nobody reports on is a key discovered to be wrong in the room.
    """
    settings.anthropic_api_key = "sk-a"
    settings.openai_api_key = "sk-b"
    settings.google_api_key = "sk-c"

    monkeypatch.setattr(
        preflight, "check_source",
        lambda role, source, s, **_: preflight.Check(ok=True, detail=f"{role}: {source.provider}"),
    )
    live = client.post("/console/check").json()["live"]

    assert set(live) == {"primary", "secondary", "google"}


def test_live_check_says_why_a_source_failed(settings, monkeypatch):
    """Not just that it failed.

    Every provider's `test_connection` swallows the exception and returns
    False, so routing this check through it could only ever produce "did not
    answer" — the one answer a trainer cannot act on.
    """
    from app.llm import router as router_module
    from app.llm.base import LLMModelNotFoundError
    from app.server.runs import ModelSource

    class Raises:
        def __init__(self, *args, **kwargs):
            pass

        def generate(self, *args, **kwargs):
            raise LLMModelNotFoundError("Model 'claude-sonnet-4-6' not found: 404")

    monkeypatch.setattr(router_module, "LLMRouter", Raises)
    source = ModelSource(provider="anthropic", model="claude-sonnet-4-6", egress="api.anthropic.com")

    check = preflight.check_source("primary", source, settings)

    assert check.ok is False
    assert "LLMModelNotFoundError" in check.detail
    assert "claude-sonnet-4-6" in check.detail


def test_a_failure_reason_never_carries_the_key(settings, monkeypatch):
    """The provider's message is not trusted to be credential-free."""
    from app.llm import router as router_module
    from app.llm.base import LLMAuthenticationError
    from app.server.runs import ModelSource

    settings.anthropic_api_key = "sk-ant-a-real-looking-value-0123456789"

    class Raises:
        def __init__(self, *args, **kwargs):
            pass

        def generate(self, *args, **kwargs):
            raise LLMAuthenticationError(f"401 invalid x-api-key {settings.anthropic_api_key}")

    monkeypatch.setattr(router_module, "LLMRouter", Raises)
    source = ModelSource(provider="anthropic", model="claude-sonnet-4-6", egress="api.anthropic.com")

    assert settings.anthropic_api_key not in preflight.check_source("primary", source, settings).detail
