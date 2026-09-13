# Banco context

Banco is the demonstration harness for Workshop 1 of the AI Translator lesson.
It runs the five demonstrations with the mechanism exposed, in one application,
on one machine.

Pedagogical vocabulary — **Banco**, **Replay**, **Data path**, **Tool category
vs. delivery vehicle**, **Workshop 1 / 2**, **Sustained transfer** — is defined
in the AI Translator repository's `CONTEXT.md` and is not restated here. This
file covers only what is local to this codebase.

## Terms

- **Harness**: the projected surface, served at `/harness`. Everything it renders
  is on a screen in front of a client's staff. It is the only route that may be
  projected; `/` and `/console` carry key fields.
- **Stage console**: the authenticated surface at `/console`, used for
  pre-flight, configuration, prompt inspection, indexing and logs. Never
  projected. It is a route on the same server, not a second application, and it
  is where Banco opens: `/` redirects here on every launch.
- **Pre-flight**: the check the console runs before a lesson — sources reachable,
  models pulled, chain files present, recordings fresh. It runs every time, not
  only on a machine that looks unconfigured.
- **Trainer field**: a demo-database field written for the trainer and never for
  the room — `lands`, `watch_for`, any `note`. Stripped server-side in
  `app/server/demos.py`.
- **Demo**: one of D1–D5. Has a *shape* (varianza, giudizio, scala, costruzione,
  attacco) and a mechanism it teaches. Two demos with the same shape is a bug.
- **Beat**: one prompt inside a demo, identified as `m<demo>-p<n>`. The unit that
  runs, records and replays.
- **Pane**: one of the side-by-side regions a beat runs in — *pannello* in
  Italian. A pane asks for a role and is bound to a model source; it never names
  a provider itself (`docs/adr/0003`). Four panes answering the same prompt at
  once is D1's whole mechanism, so panes are compared, which is why they are
  laid out together and why anything shown on one is shown on all.
- **Info**: the harness control that expands every pane's parameter strip at
  once. What a pane shows *without* it is declared by the beat, in the run
  block's `teaches_params`; a pane showing no parameter is making no claim about
  it (`docs/adr/0004`).
- **Session profile**: the named file in `demo/sessions/` that binds each role to
  a concrete provider, model and parameters, with optional per-demo overrides.
  Chosen at pre-flight, never mid-lesson, and never containing a credential. It
  supplies what a run block does not state and may not contradict what it does
  (`docs/adr/0004`).
- **Headroom**: what a provider's rate limit leaves — requests and tokens
  remaining before the next reset, read from response headers. Trainer
  information, console only, and not the same thing as account credit, which no
  provider exposes to an ordinary API key (`docs/adr/0005`).
- **Dead branch**: a beat deliberately shown to fail or to lead nowhere, marked
  in the database and announced as dead only *after* it runs.
- **Demo database**: `demo/demo-prompts.json` — prompt text, sectors,
  placeholders and, in Banco, machine-readable `run` blocks. Vendored from the
  deck at the commit in `demo/DECK-PIN.txt`.
- **Sector**: one of the ids the demo database declares — today `numismatics`,
  `photovoltaic`, `automation-software`, `defi-protocol`, `trade-association`,
  `knitwear-software`. Chosen once; drives every prompt, placeholder and folder.
  Its `data.folder` names the Italian directory under `demo/data/` and its
  `data.records_dir` the records folder D4 works over. The list is the
  database's, never a list written here: `demo/kit/` can generate a pack for
  each, and pre-flight reports which of them has one on this machine.
- **Variant**: a per-sector override of a node in the demo database
  (`variants[<sector>]`). Applied before placeholder substitution; a prompt is
  not sector-specific until it is.
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
- **Language**: Italian by default, English second, chosen per browser and never
  per server. It decides three separate things, which is why it is a term:
  which words Banco's own chrome uses, which of a beat's two prompts is *sent to
  the model*, and which language the handover file is written in. A string
  Banco generates is translated in `app/i18n.py` or in
  `app/web/shared/strings.*.js`; a string Banco carries comes from the database
  as `<field>` (English) or `<field>_it` (Italian); a string a model or a
  provider produced is never translated at all.

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
- A parameter is displayed only if the request carried it. A parameter that was
  dropped is shown as dropped, never as a value and never silently.
- A figure shown as a measurement was measured. An estimate is labelled as one,
  and "nothing was reported" renders as nothing, never as zero.
- A missing model source degrades a beat to replay; it never removes the beat.
- Dependency resolution is locked and validated **from a clean checkout** before
  a change is accepted.
- Both surfaces open in Italian, and either can be switched without leaving it.
  No language is held as process state: the harness on the projector does not
  follow the console's setting.
