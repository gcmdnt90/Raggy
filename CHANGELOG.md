# Changelog

## v0.2.0 - 2026-09-09

Milestone M0 — fork hygiene. Verified from a clean clone: 60 tests pass.

- Regenerated `requirements.lock` and `requirements-dev.lock` on Windows with
  Python 3.13 from the corrected `pyproject.toml`. `streamlit` and
  `qdrant-client` are out, `chromadb` and `fastapi` are in. `uvicorn` and
  `starlette` had been in the lock only as transitives of `streamlit`, so their
  pins carried no weight; `uvicorn` is now declared and bounded.
- Implemented three security guards that the test suite specified but that no
  version of the code has ever contained, in Banco or in Raggy. The suite had
  been red since the fork.
  - `app.utils.network.normalize_ollama_base_url` — `OLLAMA_BASE_URL` came from
    `.env` and reached `requests` with no validation. Now loopback-only and
    credential-free, enforced as a `Settings` validator, so a bad value fails
    at load rather than during a demonstration.
  - `app.utils.logging_config.cleanup_old_logs` — bounded log retention. Logs
    are where a prompt typed in a client's room lands on disk, so this is a
    confidentiality control. `logs/tokens.db` is never removed.
  - An uncompressed-size cap and ZIP member path checking in
    `app.utils.sanitize`, covering DOCX and XLSX. Both guards live in the
    helper the two formats share; XLSX previously had neither.
- `scripts/manage.py start` launched two Streamlit entry points that no longer
  exist. It now starts the one server, and `--admin` is gone: the stage console
  is a route, not a second application.
- Corrected `AGENTS.md` §3. The clean-checkout recipe imported a deleted module,
  ran `pytest` from a lock that does not contain it, and read pip-compile's own
  `--no-index` header emission as a flag someone had passed.
- One pytest configuration instead of two.

## v0.1.1 - 2026-04-27

- Added input sanitization, prompt-injection spotlighting, and system-prompt guardrails.
- Added daily token-budget tracking with SQLite persistence and router-level hard caps.
- Hardened PDF, DOCX, XLSX, Markdown, and text parsing before ingestion.
- Added chat input limits, budget status, reset controls, safer admin authentication, and localhost admin binding.
- Added operator runbook and regression tests for security-sensitive behavior.
