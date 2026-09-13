# The test suite

Run it the way `AGENTS.md` §3 prescribes — from a clean checkout, against the
locks, never in an existing `venv/`:

```bat
git clone <repo> %TEMP%\banco-clean
cd %TEMP%\banco-clean
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -c "import chromadb, app.rag.retriever, app.server.main"
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pytest tests/
```

`pytest tests/ -v` in the working `venv/` is fine while iterating, and proves
nothing on its own: both defects found on 2026-09-05 only appear on a fresh
clone, and that is exactly how they survived.

`tests/conftest.py` points every sector root at a throwaway copy of
`demo/data/`. Without it a run of the suite overwrites the shipped handover
files with stub output — which is not visible until a lesson needs one.
