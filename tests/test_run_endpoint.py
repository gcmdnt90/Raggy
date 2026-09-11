"""The run endpoint, end to end, against a stub provider.

No network and no API key: a fake provider is registered in the router's lookup
table, so this exercises the real plan, the real threads, the real SSE framing
and the real chain-file rule. What it cannot prove is that a given vendor's SDK
behaves - that is what the dry run before a lesson is for.
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.llm.base import LLMError, LLMProvider, LLMResponse
from app.llm.router import _PROVIDER_PATHS
from app.server import harness, runner, sources


class StubProvider(LLMProvider):
    """Yields a few deterministic chunks. Registered in place of a real SDK."""

    provider_name = "stub"
    default_model = "stub-1"
    fail = False

    def available_models(self):
        return [self.default_model]

    def generate(self, messages, *, model=None, temperature=None, max_tokens=None):
        return LLMResponse(content="stub", model=model or self.default_model,
                           provider=self.provider_name)

    def generate_stream(self, messages, *, model=None, temperature=None, max_tokens=None):
        if type(self).fail:
            raise LLMError("stub refused on purpose")
        # Echo the temperature so a test can prove each pane was sent its own.
        yield from ("draft ", f"t={temperature} ", f"turns={len(messages)}")

    def test_connection(self):
        return True

    def embed(self, texts, *, model=None):
        return [[0.0] for _ in texts]


@pytest.fixture
def client(monkeypatch, tmp_path):
    """A server whose providers are stubs and whose budget file is disposable."""
    monkeypatch.setitem(_PROVIDER_PATHS, "anthropic", (__name__, "StubProvider"))
    monkeypatch.setitem(_PROVIDER_PATHS, "openai", (__name__, "StubProvider"))
    monkeypatch.setattr(StubProvider, "fail", False)

    # Two API keys present, Ollama deliberately not consulted: the profile under
    # test is `classroom`, and a real reachability probe would make this test
    # depend on whether the developer happens to be running Ollama.
    class Settings:
        anthropic_api_key = "test-key"
        openai_api_key = "test-key"
        google_api_key = ""
        ollama_base_url = "http://127.0.0.1:11434"
        llm_provider = "anthropic"
        llm_model = "stub-1"
        max_tokens = 64

    monkeypatch.setattr(harness, "get_settings", lambda: Settings())
    monkeypatch.setattr(
        sources, "ollama_source", lambda settings, check=True: None
    )
    runner.reset_transcripts()

    app = FastAPI()
    app.include_router(harness.router)
    return TestClient(app)


def events(response) -> list[tuple[str, dict]]:
    out = []
    for block in response.text.split("\n\n"):
        if not block.strip():
            continue
        name, data = "message", "{}"
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[7:].strip()
            elif line.startswith("data: "):
                data = line[6:]
        out.append((name, json.loads(data)))
    return out


def run(client, beat_id="m1-p1", sector="numismatics"):
    return client.post("/api/run", json={
        "demo_id": "m1", "beat_id": beat_id, "sector": sector,
    })


# ── the stream ──────────────────────────────────────────────────────────────

def test_run_streams_plan_first_and_run_done_last(client):
    got = events(run(client))
    assert got[0][0] == "plan"
    assert got[-1][0] == "run_done"


def test_plan_event_exposes_the_mechanism_for_every_pane(client):
    """Objective 2: provider, model, temperature and destination, per pane."""
    plan = events(run(client))[0][1]
    assert len(plan["panes"]) == 4
    for pane in plan["panes"]:
        assert pane["provider"] and pane["model"]
        assert pane["temperature"] == 1.0
        assert pane["egress"]
    assert plan["prompt"] and "[PASTE RAW NOTES]" not in plan["prompt"]
    assert plan["replayed"] is False


def test_every_pane_streams_and_finishes(client):
    got = events(run(client))
    assert {e[1]["pane"] for e in got if e[0] == "delta"} == {0, 1, 2, 3}
    assert {e[1]["pane"] for e in got if e[0] == "pane_done"} == {0, 1, 2, 3}


def test_each_pane_is_sent_its_own_temperature(client):
    """The stub echoes what it was given, so this is not self-reported."""
    got = events(run(client))
    text = "".join(e[1]["text"] for e in got if e[0] == "delta")
    assert "t=1.0" in text


def test_plan_response_never_carries_a_credential(client):
    body = run(client).text
    assert "test-key" not in body
    assert "api_key" not in body


# ── the chain ───────────────────────────────────────────────────────────────

def test_successful_run_overwrites_the_chain_file(client, tmp_path, monkeypatch):
    """Invariant 3: a successful run overwrites the handover file."""
    from app.server import demos
    root = tmp_path / "numismatica"
    (root / "demo" / "catena").mkdir(parents=True)
    (root / "demo").joinpath("m4-grezzi.md").write_text("raw notes here", encoding="utf-8")
    chain = root / "demo" / "catena" / "d1-bozze.md"
    chain.write_text("SHIPPED FALLBACK", encoding="utf-8")
    monkeypatch.setattr(demos, "data_root", lambda sector: root)
    monkeypatch.setattr(runner, "data_root", lambda sector: root)
    import app.server.runs as runs_mod
    monkeypatch.setattr(runs_mod, "data_root", lambda sector: root)

    done = [e for e in events(run(client)) if e[0] == "run_done"][0][1]
    assert done["produced"] == "demo/catena/d1-bozze.md"
    written = chain.read_text(encoding="utf-8")
    assert "SHIPPED FALLBACK" not in written
    assert "temperature 1.0" in written, "the header must say what produced each draft"


def test_failed_run_leaves_the_chain_file_intact(client, tmp_path, monkeypatch):
    """Invariant 3: a failed run is narrated and the shipped file stays."""
    from app.server import demos
    root = tmp_path / "numismatica"
    (root / "demo" / "catena").mkdir(parents=True)
    (root / "demo").joinpath("m4-grezzi.md").write_text("raw notes here", encoding="utf-8")
    chain = root / "demo" / "catena" / "d1-bozze.md"
    chain.write_text("SHIPPED FALLBACK", encoding="utf-8")
    for mod in (demos, runner):
        monkeypatch.setattr(mod, "data_root", lambda sector: root)
    import app.server.runs as runs_mod
    monkeypatch.setattr(runs_mod, "data_root", lambda sector: root)
    monkeypatch.setattr(StubProvider, "fail", True)

    got = events(run(client))
    assert [e for e in got if e[0] == "pane_failed"], "a provider failure must be narrated"
    done = [e for e in got if e[0] == "run_done"][0][1]
    assert done["produced"] is None
    assert done["chain_held"] is True
    assert chain.read_text(encoding="utf-8") == "SHIPPED FALLBACK"


# ── continuation ────────────────────────────────────────────────────────────

def test_second_beat_carries_the_first_beats_exchange_per_pane(client):
    """m1-p2 must interrogate what its own pane wrote, not start fresh."""
    run(client, "m1-p1")
    got = events(run(client, "m1-p2"))
    text = "".join(e[1]["text"] for e in got if e[0] == "delta")
    # One user turn alone would be turns=1; the prior exchange makes it three.
    assert "turns=3" in text, "the previous exchange was not carried forward"


def test_reset_forgets_the_exchange_so_a_rehearsal_does_not_leak(client):
    run(client, "m1-p1")
    assert client.post("/api/transcripts/reset").json()["status"] == "cleared"
    got = events(run(client, "m1-p2"))
    text = "".join(e[1]["text"] for e in got if e[0] == "delta")
    assert "turns=1" in text


# ── degradation and refusal ─────────────────────────────────────────────────

def test_one_key_degrades_but_still_shows_four_panes(client, monkeypatch):
    monkeypatch.setattr(harness, "get_settings", lambda: type("S", (), {
        "anthropic_api_key": "k", "openai_api_key": "", "google_api_key": "",
        "ollama_base_url": "http://127.0.0.1:11434", "llm_provider": "anthropic",
        "llm_model": "stub-1", "max_tokens": 64,
    })())
    got = events(run(client))
    plan = got[0][1]
    assert plan["degraded"] is True
    assert len(plan["panes"]) == 4
    unavailable = [e[1] for e in got if e[0] == "pane_unavailable"]
    assert len(unavailable) == 2
    for entry in unavailable:
        assert entry["reason"]
        assert entry["recording"] is None, "there are no recordings yet (M3)"


def test_unavailable_panes_emit_no_text(client, monkeypatch):
    """AGENTS.md rule 1: never render output no model produced."""
    monkeypatch.setattr(harness, "get_settings", lambda: type("S", (), {
        "anthropic_api_key": "k", "openai_api_key": "", "google_api_key": "",
        "ollama_base_url": "http://127.0.0.1:11434", "llm_provider": "anthropic",
        "llm_model": "stub-1", "max_tokens": 64,
    })())
    got = events(run(client))
    silent = {e[1]["pane"] for e in got if e[0] == "pane_unavailable"}
    spoke = {e[1]["pane"] for e in got if e[0] == "delta"}
    assert not (silent & spoke)


def test_library_beat_is_refused_with_the_reason(client):
    res = run(client, "m1-p3")
    assert res.status_code == 409
    assert "temperature" in res.json()["detail"].lower()


def test_unknown_beat_is_a_404(client):
    assert run(client, "m1-p99").status_code == 404


# ── what the harness is allowed to know ─────────────────────────────────────

def test_status_reports_the_profile_without_any_credential(client):
    body = client.get("/api/status")
    assert body.status_code == 200
    data = body.json()
    assert data["profile"] == "classroom"
    assert "test-key" not in body.text
    for role in data["roles"].values():
        assert set(role) == {"provider", "model", "egress", "local"}


def test_demo_listing_annotates_which_beats_can_run(client):
    demo = client.get("/api/demos/m1?sector=numismatics").json()
    runs_by_id = {b["id"]: b["run"] for b in demo["prompts"]}
    assert runs_by_id["m1-p1"]["runnable"] is True
    assert runs_by_id["m1-p1"]["panes"] == 4
    assert runs_by_id["m1-p3"]["runnable"] is False
    assert runs_by_id["m1-p3"]["reason"]


# ── credentials reach the provider, and only the provider ───────────────────

def test_the_provider_is_constructed_with_its_api_key(client, monkeypatch):
    """Without this the provider raises 'API key missing' and no pane runs.

    The stub needs no key, so nothing else in this file would notice.
    """
    seen = {}
    original = StubProvider.__init__

    def spy(self, *args, **kwargs):
        seen.update(kwargs)
        original(self, *args, **kwargs)

    monkeypatch.setattr(StubProvider, "__init__", spy)
    run(client)
    assert seen.get("api_key") == "test-key"


def test_ollama_is_constructed_with_the_configured_base_url(monkeypatch):
    """A trainer who moved Ollama off the default port must still be reached."""
    class Settings:
        anthropic_api_key = ""
        openai_api_key = ""
        google_api_key = ""
        ollama_base_url = "http://127.0.0.1:9999"
        llm_provider = "ollama"
        llm_model = "qwen3:8b"

    assert sources.provider_kwargs("ollama", Settings()) == {
        "base_url": "http://127.0.0.1:9999"
    }


def test_a_model_that_ignores_temperature_is_reported_as_such():
    """Objective 2 is only served if what is displayed is true."""
    assert sources.temperature_applies("anthropic", "claude-sonnet-4-6") is True
    assert sources.temperature_applies("anthropic", "claude-opus-4-8") is False
    assert sources.temperature_applies("ollama", "anything") is True
