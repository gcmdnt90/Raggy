# Operator runbook

What to do before, during and after a lesson. Everything here is a property of
the code as it stands; nothing is aspirational.

This file described Raggy until 2026-09-13 — two Streamlit applications, an
admin panel on `127.0.0.1:8502`, a red budget banner, a "Reset conversation"
sidebar button. None of those exist in Banco, and a trainer following it would
have spent the minutes before a lesson looking for an application that was never
started.

## Before the lesson

1. `start.bat`. Banco serves both surfaces from `127.0.0.1:8501` and opens
   **pre-flight** at `/console`. It opens there on every launch, not only on a
   machine that looks unconfigured.
2. Work down the console until nothing is marked `··`:
   - **Model sources** — at least one key or a reachable Ollama. Two make every
     pane of D1 live.
   - **Demo material** — the sector's pack, checked for all five demos. A
     missing pack prints the `demo/kit/generate.py` command that creates it,
     `--out` included.
   - **Readiness** — the chain files, the console password, the recordings.
3. Press **Run the full check**. It spends one real call per configured source
   and is the only line that can tell a working key from a stored one. Nothing
   else on the page distinguishes a rotated key from a good one.
4. Press **Forget rehearsal transcripts** if you have run a beat today. A beat
   marked `continues` interrogates what its own pane said earlier; after a dry
   run those answers are still in memory and the room would watch a model be
   asked about an answer it gave before the lesson started.
5. Project `/harness`, and only `/harness`. `/` redirects to the console and the
   console carries key fields.

## During the lesson

- The egress chip on the harness is an instrument, not decoration: D5-A's
  network-off gesture proves nothing unless the room watched something leave.
- A pane with no source says so and shows nothing. There is no recording to
  replay yet (M3), so there is nothing to fall back to and nothing is invented.
- A failed run leaves the handover file it produces untouched, so the shipped
  version is still there to open and read out. Invariant 3: the chain never
  waits.
- The language switch is on both surfaces. It is per browser: changing the
  console does not change the projector.

## After the lesson

- Logs are the one place a prompt typed in a client's room reaches disk.
  `logs/` is gitignored and swept on startup — 14 days by default
  (`DEFAULT_LOG_RETENTION_DAYS`). Shorten it if the machine leaves your hands.
- `logs/tokens.db` records measured usage per day. It is never swept, and
  nothing refuses a call on the strength of it (ADR 0005).
- A successful run overwrote the handover files for that sector. That is
  intended; `git status` shows which, and `git checkout` restores the shipped
  ones if a rehearsal produced something you do not want to keep.

## Quick checks

- `GET /healthz` answers `{"status": "ok"}`.
- Both surfaces bind to loopback only (`app/server/main.py: run()`).
- Every console route is authenticated once a password is set; before that the
  console says loudly that it is not.
- No key, no client name, no `_perito/ground-truth.csv`, no trainer note ever
  reaches `/harness` — enforced server-side in `app/server/demos.py` and checked
  in `tests/test_harness_invariants.py`.
