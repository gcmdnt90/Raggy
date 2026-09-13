# 4. Session profiles bind roles to sources

Date: 2026-09-12
Status: Accepted
Extends: [0003](0003-run-blocks-live-in-banco.md)
See also: [0005](0005-usage-is-measured-headroom-is-not-credit.md) for the
token ceilings this decision would otherwise have had to raise.

## Context

ADR 0003 settled where a run block lives and what it may not contain: no prompt
text, and **no provider name**. A pane asks for a role — `primary`, `secondary`,
`local` — and something else binds that role to a concrete source. That
indirection is what lets a missing source degrade a beat to replay instead of
removing it.

The something else is `app/server/sources.py`, and today it decides by
arithmetic rather than by choice:

- `API_ORDER = ("anthropic", "openai", "google")`. The first provider with a key
  becomes `primary`, the second `secondary`. The binding is a consequence of
  which keys happen to be in `.env`, in an order written in the source.
- The model is `_load_provider_class(provider).default_model` — one string per
  provider class, the same for every beat of every lesson.
- `.env`'s `LLM_MODEL` reaches exactly one place: `ollama_source`, and only when
  `LLM_PROVIDER == "ollama"`. For the three API providers it is inert.

Three consequences, in increasing order of how much they cost in a room:

1. **The trainer cannot choose a model.** Changing which Claude answers D1 means
   editing `AnthropicProvider.default_model`. That is a code edit for a value
   the same repository already argues is data (`run-blocks.json`,
   `_temperature_note`: *"The value is data, not code"*).
2. **A configured provider can fill no pane.** There are three API keys and two
   API roles. With all three set, Google is called once by `live_checks` — which
   was added precisely so a key nobody reports on cannot exist — and then never
   runs a beat.
3. **Every demo in a lesson gets the same two models.** D1 wants two API
   providers at temperature 1.0. D2 wants capability *difference*, which is the
   mechanism it teaches. One global binding cannot serve both, so D2's
   difference has to be described rather than performed — the failure mode
   PROJECT.md was written against.

A fourth pressure arrives with the parameters themselves. `Pane.thinking` is
declared in the run-block schema, carried on the pane, and emitted to the
harness by `_pane_payload` — and no provider signature accepts it. Nothing
sends it. The harness would render a thinking budget beside a call that carried
none, which is the exact false statement `temperature_is_applied` exists to
prevent. `m2-p2`'s `_unblocked` entry already says so.

So the question is not only "which model" but "which parameters, and did they
arrive" — and the second half has to be answered structurally, because a
hard-coded capability table is a claim about four vendors' APIs that will be
wrong between two lessons. Google's own thinking parameter changed shape
between the 2.5 and 3.x generations; `gemini-2.5-flash` began answering 404
under Banco between one delivery and the next.

## Decision

**1. The run-block contract is unchanged.** A pane still asks for a role and
still never names a provider. Nothing in `demo/run-blocks.json` changes.

**2. A new object binds roles to sources: the session profile.** It lives in
`demo/sessions/<name>.json`, several may exist, one is active. It names
providers, models and parameters; it never contains a credential. Keys stay
write-only in `.env`, where ADR 0002 and AGENTS.md rule 2 put them.

**3. A session profile has defaults and per-demo overrides.** `defaults` binds
the three roles for the whole lesson; `demos.<demo_id>` rebinds any of them for
one module. All three roles are always overridable, from every demo, and a role
left alone inherits visibly rather than silently. This is what lets D1 run on
two API providers while D2 runs the same role on a large and a small model.

**4. The run block wins wherever it speaks.** A parameter stated on a pane in
`run-blocks.json` — today `temperature`, tomorrow `thinking` — is pedagogy, and
a session profile may not override it. The profile supplies the binding, and
defaults for parameters the run block leaves unstated. Without this rule a
profile could quietly set D1's four panes to temperature 0.3 and the demo would
run, look fine, and teach nothing.

Precedence, most specific first:

    run-block pane  >  session profile: demos.<demo_id>  >  session profile: defaults  >  provider default

**5. Binding is chosen at pre-flight, not mid-lesson.** The active profile is
read when a beat is planned. Nothing re-reads configuration while a stream is
open, and no picker goes on the projected surface.

**6. The harness renders what was sent, not what was asked.** Each provider
builds its request in one inspectable step before the call and reports two
things: the parameters that went into the payload, and the parameters that were
dropped with the reason. The pane event carries those, not the pane's
intentions. `temperature_is_applied` becomes one instance of a general rule
rather than the only parameter that has one.

This is the load-bearing half of the decision. A capability table decides what
the console *offers*; it may drift, and when it does the cost is a control that
turns out to be unavailable — visibly, at pre-flight or on the pane. The table
never decides what the room is told.

**7. The beat decides what the room sees without asking.** A run block declares
`teaches_params` — the parameters that beat exists to make visible. Those render
on the collapsed pane; everything else lives behind one **Info** control in the
harness header that expands the full parameter strip on all four panes at once.
D1 therefore shows temperature on four panes with no gesture, and D3, which
teaches nothing about sampling, does not carry a temperature the room has to
ignore.

One control, not four: a room comparing panes needs them to expand together, and
four separate reveals is three panes out of step. A per-pane click remains for
the long text — the system prompt and the prompt as sent. The egress indicator is
outside this mechanism and stays permanently visible; invariant 4 only works if
the room watched calls leave *before* D5-A turns the network off.

Collapsed is silent, not vague. A pane that is not showing a parameter is making
no claim about it, which is why hiding is safe and a stale display is not.

**8. `teaches_params` is checked, not trusted.** Pre-flight asks, for each demo:
does at least one bound pane's model actually apply the parameter this demo
teaches? The capability table answers on page load; `POST /console/check`
proves it with a real call that reports what was dropped. A demo whose only
temperature knob is bound to a model that ignores temperature is a demo that
will run, look fine and teach nothing — and that is a pre-flight line, not a
discovery in a room.

## Consequences

- `sources.py` stops deriving a binding and starts reading one. `API_ORDER`
  survives only as the order the console lists providers in; `_default_model`
  becomes the value a profile is seeded with, not the value that is used.
- Any provider can hold any role. The three-keys-and-Google-never-runs case
  disappears, and so does the Ollama pane silently falling back to `gemma3:4b`
  when `LLM_PROVIDER` is not `ollama`.
- `.env` keeps credentials, endpoints and embeddings. `LLM_PROVIDER` and
  `LLM_MODEL` no longer decide anything about a pane; one new scalar,
  `SESSION_PROFILE`, names the active file.
- Provider classes gain a request-building step. It is pure, takes no network,
  and is therefore the first thing about the provider layer that can be tested
  exhaustively — which is how the `anthropic==1.2.0` temperature defect should
  have been caught.
- Two profiles can differ in ways that make a beat unrunnable (a `thinking`
  budget on a model that has no thinking). Pre-flight has to check the active
  profile as configured, not just the key: `POST /console/check` sends the
  session's real parameters and reports what was dropped.
- One more file must be kept in step with beat ids, as `run-blocks.json`
  already is. A per-demo override naming a demo that does not exist is a
  test failure, not a discovery in a room.
- The token ceilings go rather than move. `HARD_MAX_TOKENS = 4000` and
  `Settings.max_tokens <= 4000` make a thinking budget arithmetically
  impossible — Anthropic requires `budget_tokens >= 1024` and strictly less than
  `max_tokens` — but raising them to a larger arbitrary number only moves where
  the refusal lands. ADR 0005 removes them and puts an instrument in their place.
- `run-blocks.json` gains one field, `teaches_params`. It is data about
  execution, not prompt text, so it sits inside ADR 0003's contract. A beat that
  declares nothing keeps its parameters behind Info, which is the safe default.
- The harness gains a control. It was cleared under AGENTS.md section 7 on
  2026-09-12, on the understanding that the collapsed pane shows only what the
  beat declares and the egress indicator stays put.

## Alternatives considered

**Name the provider and model in the run block.** The most direct reading of
"more control per demo". Rejected: it is the one thing ADR 0003 forbids, and for
a reason that still holds — a block naming `anthropic` cannot run under the
`offline` profile and cannot degrade to replay. It also puts a per-client
decision in a file that is otherwise per-lesson, so two clients would mean two
run-block sets.

**Keep it in `.env`, one variable per role.** No new file, no new concept:
`PRIMARY_PROVIDER`, `PRIMARY_MODEL`, and so on. Rejected on the requirement
itself — per-demo overrides do not fit in a flat key-value file, and two saved
lesson setups cannot coexist. `.env` also mixes secrets with configuration, and
this configuration is the half that should be readable, diffable and committed.

**Let the console write the binding into the vendored demo database.** Rejected
by ADR 0001: that file is byte-identical to its pin, and the divergence check is
a byte comparison precisely so it cannot be taught to ignore things.

**A capability matrix as the source of truth for what was sent.** Rejected. It
is a table of other people's APIs maintained in this repository, and it would be
consulted to decide what to put on a projector. When it is wrong the room is
told something false and nothing fails. Reporting the built payload cannot be
wrong in that direction.

**A model picker on the harness.** Rejected under AGENTS.md rule 2 and section
7: it is configuration, it belongs to the console, and the room should be
watching a mechanism rather than a trainer choosing one.

**Every parameter always visible on every pane, as today.** Rejected once the
set grew. Provider, model, temperature and egress fit on one line; add
`max_tokens`, a thinking budget, a dropped-parameter caveat and token counts and
the line becomes a wall the room reads instead of the output. Worse, it would
carry a temperature through D3 and D5, where sampling is not the mechanism and
the number is noise competing with the one that matters.

**A "?" on each pane.** Rejected as the primary control for the reason in
decision 7 — four gestures where the demonstration needs one. Kept as the
secondary control for per-pane detail.
