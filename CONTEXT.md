# Banco context

Banco is the demonstration harness for Workshop 1 of the AI Translator lesson.
It runs the five demonstrations with the mechanism exposed, in one application,
on one machine.

Pedagogical vocabulary — **Banco**, **Replay**, **Data path**, **Tool category
vs. delivery vehicle**, **Workshop 1 / 2**, **Sustained transfer** — is defined
in the AI Translator repository's `CONTEXT.md` and is not restated here. This
file covers only what is local to this codebase.

## Terms

- **Harness**: the projected surface, served at `/`. Everything it renders is on
  a screen in front of a client's staff.
- **Stage console**: the authenticated surface at `/console`, used for
  pre-flight, configuration, prompt inspection, indexing and logs. Never
  projected. It is a route on the same server, not a second application.
- **Trainer field**: a demo-database field written for the trainer and never for
  the room — `lands`, `watch_for`, any `note`. Stripped server-side in
  `app/server/demos.py`.
- **Demo**: one of D1–D5. Has a *shape* (varianza, giudizio, scala, costruzione,
  attacco) and a mechanism it teaches. Two demos with the same shape is a bug.
- **Beat**: one prompt inside a demo, identified as `m<demo>-p<n>`. The unit that
  runs, records and replays.
- **Dead branch**: a beat deliberately shown to fail or to lead nowhere, marked
  in the database and announced as dead only *after* it runs.
- **Demo database**: `demo/demo-prompts.json` — prompt text, sectors,
  placeholders and, in Banco, machine-readable `run` blocks. Vendored from the
  deck at the commit in `demo/DECK-PIN.txt`.
- **Sector**: `numismatica` / `fotovoltaico` / `automazione`. Chosen once; drives
  every prompt, placeholder and folder.
- **Chain**: the five handover files `d1-bozze.md` … `d5-verifiche-umane.md`.
  Each demo consumes the previous demo's output.
- **Recording**: a captured real run of a beat, replayable. Not a fixture, not a
  mock — a recording of something a model actually produced.
- **Model source**: one configured way to get a completion — an API provider or a
  local Ollama model. At least one required; two recommended.
- **Profile**: `classroom` / `take-home` / `offline` — the one first-run choice
  that determines which beats run live and which replay.
- **Egress indicator**: the persistent display of where each request went. It is
  the instrument for the cloud-vs-local threshold-concept family, not decoration.

## Invariants

- The harness never renders a credential, a client name, a ground-truth file, or
  a trainer note. (Extends Raggy's original rule that the user app must not
  expose credentials or administrative controls.)
- The stage console requires authentication and binds to loopback.
- Secrets are write-only values, redacted from logs, and live only in `.env`.
- The vector store is embedded and on disk; it is never exposed as a network
  service.
- Every model call displays its destination.
- Output that no model produced is never displayed. Replay is announced.
- A missing model source degrades a beat to replay; it never removes the beat.
- Dependency resolution is locked and validated **from a clean checkout** before
  a change is accepted.
