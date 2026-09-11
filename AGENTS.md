# AGENTS.md — instructions for AI agents working on Banco

Read this before touching anything. Then read `PROJECT.md` for what Banco is,
and `CONTEXT.md` for what the words mean.

This file governs agents that **develop, install or repair** Banco. It is not
participant-facing material.

---

## 1. What this repository is

Banco is the demonstration harness for Workshop 1 of the AI Translator lesson.
It is a **fork of Raggy** (`git remote raggy`), which is a different tool with a
different job and is still maintained separately.

**One FastAPI server, two surfaces as routes** (`docs/adr/0002`):

| Route | Surface | Notes |
|---|---|---|
| `/` | redirect to `/console` | Banco opens on pre-flight, every launch |
| `/harness` | **the harness** — what the room sees | projected; no credentials, no trainer material |
| `/console` | **the stage console** — pre-flight and configuration | authenticated, never projected |

`/` used to be the harness. It now redirects to pre-flight, because a check that
runs only when Banco thinks it is needed is not a check: the machine that fails
is the one that worked last week. **`/harness` is the only URL safe to put on a
projector** — `/` and `/console` show key fields.

`start.bat` (or `scripts/start.sh`) launches `python -m app.server.main` on
`127.0.0.1:8501` and opens pre-flight. `admin.bat` only opens the console route —
it does not start a second application. There is no Streamlit in this repository; do not reintroduce
it, and do not add a second server, port or UI framework.

Read order for a new agent: `PROJECT.md` → this file → `CONTEXT.md` →
`docs/adr/` → the AI Translator `docs/adr/0001–0003`.

---

## 2. Installing Banco — the agent-executable contract

An agent asked to install Banco should be able to run this unattended up to the
key step, and to guide a non-technical person through the rest.

**Preconditions to verify, not assume**

    python --version        # 3.10 <= x < 3.14, per pyproject.toml
    git --version

**Steps**

1. `git clone <banco-url> Banco && cd Banco`
2. `python -m venv venv`
3. `venv/Scripts/python -m pip install --upgrade pip` (Windows) or
   `venv/bin/python -m pip install --upgrade pip`
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`.
6. **Stop here and ask the human.** An agent cannot obtain an API key. Present
   the four options — Anthropic, OpenAI, Google, or local Ollama — explain that
   at least one is required and two are recommended, and wait. Do not fabricate
   a key, do not skip to a profile the human did not choose.
7. If Ollama was chosen or is wanted as a second source, `scripts/setup_wizard.py`
   detects hardware, installs Ollama and pulls a model. It can run unattended.
8. Verify before declaring success (see §3).

**Resumability.** Installation must be resumable at step 6. A human who leaves
and comes back must not have to restart.

**Never** write an API key into a file the agent then reports, echoes, or
commits. `.env` is gitignored; keep it that way.

---

## 3. Verification — from a clean checkout, always

Banco exists partly because its parent was never validated this way. Two defects
were found on 2026-09-05 that only appear on a fresh clone (see
`Raggy/logs/FIXME-vectorstore-dependency.md`). Both are fixed here. Do not let
them come back.

Windows, PowerShell - this is the platform Banco is delivered on:

    git clone <repo> $env:TEMP\banco-clean
    Set-Location $env:TEMP\banco-clean
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.lock
    .\.venv\Scripts\python.exe -c "import chromadb, app.rag.retriever, app.server.main"
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
    .\.venv\Scripts\python.exe -m pytest tests/

Linux or Mac, for a developer not on the delivery platform:

    git clone <repo> /tmp/banco-clean && cd /tmp/banco-clean
    python -m venv .venv && .venv/bin/pip install -r requirements.lock
    .venv/bin/python -c "import chromadb, app.rag.retriever, app.server.main"
    .venv/bin/pip install -r requirements-dev.lock && .venv/bin/pytest tests/

The two installs are deliberate and in that order. `requirements.lock` is what
`start.bat` gives a participant, so it is verified alone first; `pytest` lives
only in `requirements-dev.lock`, which is a superset, so the test step needs it.

**Testing in an existing `venv/` proves nothing** — that is exactly how both
defects survived. If you change dependencies, regenerate the locks and re-run
the above in a scratch directory.

### Regenerating the locks

`pyproject.toml` declares ranges; the `.lock` files are the exact resolved set,
including transitive dependencies, and are what `start.bat` actually installs.
They are generated, never hand-edited. Run this **on Windows**, where Banco is
delivered - the existing lock was resolved on Windows with Python 3.13 and
carries no platform markers, so resolving it on Linux would silently produce a
different set:

    venv\Scripts\python -m pip install pip-tools
    venv\Scripts\python -m piptools compile --strip-extras -o requirements.lock pyproject.toml
    venv\Scripts\python -m piptools compile --extra dev --strip-extras -o requirements-dev.lock pyproject.toml

Do **not** add `--no-index` - it would stop pip-compile reaching PyPI. The
`--no-index` token in the lock header is not a record of a flag anyone passed:
pip-compile emits it itself, and it reappears in every regenerated header. An
earlier revision of this file read that token as a passed flag; it is not one.

Then cap the newly declared dependencies in `pyproject.toml` at the next version
the house style allows, and re-run the clean-checkout verification above.

**Done 2026-09-09 (M0).** Both locks were regenerated on Windows with Python
3.13 from the corrected `pyproject.toml`. `streamlit` and `qdrant-client` are
gone; `chromadb==1.5.9` and `fastapi==0.141.1` are in. `uvicorn==0.52.4` and
`starlette==1.6.0` were previously in the lock only as transitives of
`streamlit`, so their old pins carried no weight; `uvicorn` is now a declared
dependency and `starlette` comes via `fastapi`. `fastapi` and `uvicorn` are
capped at `<0.142` and `<0.53` - next minor, matching how every other 0.x
dependency here is bounded. Both are tighter than the lock needs, because the
lock is the reproducibility mechanism; loosen them if the cap starts costing an
edit per upstream release.

---

## 4. Rules you must not break

1. **Replay, never simulation.** Banco may replay a recording of a real model
   run, announced as a recording. Banco must never render output that no model
   produced — not as a placeholder, not as an illustration, not behind a label.
   The lesson teaches participants to distrust confident unverifiable output;
   fabricating one forfeits it. See AI Translator `docs/adr/0003`.

2. **Keep the projected surface clean.** `app/main.py` and everything it renders
   must never show an API key or a client name — those are confidential, and this
   extends Raggy's invariant that the user app must not expose credentials. It
   must also not show `_perito/ground-truth.csv`, `LEGGIMI-CATENA.md` or any
   trainer note: those *are* published with the repository on purpose, so this
   half of the rule is about focus, not secrecy. When in doubt it belongs in the
   stage console.

3. **Never invent facts about the client's business.** If a prompt, fixture or
   recording needs a detail you do not have — their grading scale, their document
   names, what their staff do all day — **stop and ask**. A plausible invented
   business detail is worse than an empty placeholder, because it is discovered
   live, in front of the client, by the one person who knows it is wrong. This
   rule is inherited verbatim from `theory-deck/PROMPTS.md` and applies here too.

4. **Trainer fields are stripped server-side, once.** `app/server/demos.py`
   removes `lands`, `watch_for` and every `note` before a demo reaches the
   harness. Do not filter client-side instead, and do not add a route that
   returns the raw database to the projected surface.

5. **Prompts live in the database, not in code.** `demo/demo-prompts.json` is the
   single source of truth for prompt text, shared with the deck. Editing a prompt
   in a Python file is a bug. See `docs/adr/0001`.

6. **Do not vendor an agent framework.** The agent loop must stay small enough to
   put on a projector — that is the point of it. Hermes Agent and OpenClaw are
   both MIT and both the wrong shape (messaging-gateway personal agents, not
   teaching harnesses). Borrow ideas, cite them, do not copy the codebase.

7. **Do not delete a prompt or a recording that stopped working.** Archive it
   with the date and what changed, as `PROMPTS.md` requires. Models change; the
   record of how they changed is teaching material.

8. **The chain never waits.** Handover files `d1-bozze.md` … `d5-verifiche-umane.md`
   must exist on disk before a lesson. A successful run overwrites; a failed run
   leaves the file intact.

---

## 5. Where things are

    app/server/main.py     the FastAPI app; mounts both surfaces
    app/server/harness.py  routes for the projected surface
    app/server/console.py  routes for the stage console
    app/server/demos.py    reads the demo database; strips trainer fields
    app/web/harness/       the projected page (HTML/CSS/JS, no build step)
    app/web/console/       the console page
    app/llm/               providers, router, model catalog, Ollama bootstrap
    app/rag/               embeddings, retriever, pipeline — D3 rung 3, D5-A
    app/parsers/           pdf, docx, xlsx, text
    demo/demo-prompts.json vendored copy of the deck's prompt database
    demo/DECK-PIN.txt      the theory-deck commit that copy came from
    demo/data/<sector>/    demo material per sector
    demo/kit/              generators for the demo material
    recordings/            captured runs for replay (see ADR 3)
    docs/adr/              implementation decisions
    logs/                  gitignored; scratch notes are fine here

---

## 6. Working with the fork

    git fetch raggy
    git log raggy/master --oneline        # what changed upstream
    git cherry-pick <sha>                 # take a provider fix

Fork point: `751e16c` ("security and AGENT.md update"), plus the work that was in
flight in Raggy's working copy on 2026-09-05.

Fix provider bugs **in Banco first** — it is the one that runs in front of a
room — then offer them upstream.

---

## 7. When you are unsure

Ask. This project is delivered live to paying clients by one person with a
clock running. A wrong guess that survives to the room costs more than a
question. In particular, stop and ask before: changing what a demo teaches,
changing prompt text, adding a first-run question, or making anything new appear
on the projected surface.
