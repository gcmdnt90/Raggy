# Model control — implementation spec

Implements [ADR 0004](../adr/0004-session-profiles-bind-roles-to-sources.md).
Read that first: it says *why* the binding moved and what may not be overridden.
This file says what to build.

Scope: choosing the provider and model per role and per demo, sending the
parameters a beat needs, and proving on screen that they arrived. Token counts
and rate-limit headroom are [ADR 0005](../adr/0005-usage-is-measured-headroom-is-not-credit.md)
and [its spec](usage-and-headroom.md). Out of scope: recordings (M3), the agent
loop (M5).

---

## 1. The session profile

One file per saved configuration, `demo/sessions/<name>.json`. Committed, no
credentials, safe to read aloud.

```json
{
  "version": 1,
  "name": "classroom-due-api",
  "updated": "2026-09-12",
  "note": "Anthropic + Google live, qwen3 locale per il pannello offline",

  "defaults": {
    "primary":   {"provider": "anthropic", "model": "<from live discovery>",
                  "params": {"max_tokens": 16000}},
    "secondary": {"provider": "google",    "model": "<from live discovery>",
                  "params": {"max_tokens": 8000}},
    "local":     {"provider": "ollama",    "model": "qwen3:8b",
                  "params": {"max_tokens": 4000}}
  },

  "demos": {
    "m2": {
      "primary":   {"provider": "ollama", "model": "qwen3:8b",
                    "params": {"think": "high"}},
      "secondary": {"provider": "ollama", "model": "qwen3:1.7b",
                    "params": {"think": false}}
    }
  }
}
```

Rules:

- A role entry is `{provider, model, params}`. `params` is Banco's own
  vocabulary (§3), never a vendor payload.
- `demos` is keyed by demo id (`m1`…`m5`), and a demo entry may rebind one role
  and leave the others on the defaults. Merge is per role, not per file.
- Model ids are **never hard-coded into the shipped profile**. A profile is
  written by the console from what discovery returned, so the file records a
  choice a human made from a live list. A profile whose model no longer exists
  fails at pre-flight with the provider's own 404 and the live list beside it —
  which is what `_models_hint` already does, and must keep doing.
- No key, no `base_url`, no password. `provider_kwargs` stays the only path
  credentials take into the process.

Active profile: `SESSION_PROFILE=<name>` in `.env`, one scalar, written by the
console through `save_settings_to_env`. Absent or unreadable → today's derived
binding, unchanged, so an existing install keeps working and a corrupt profile
degrades rather than blocks.

### Resolution

`app/server/sessions.py` (new), one function:

```python
def resolve(settings, demo_id: str | None) -> dict[str, ModelSource]
```

1. Load the active profile; fall back to `sources.available_sources` if none.
2. For each role: `demos[demo_id][role]` if present, else `defaults[role]`.
3. Drop a role whose provider has no key (API) or whose Ollama is not answering
   — `ollama_source`'s existing probe. **A dropped role stays dropped**; it does
   not slide onto another provider. `bind_panes` then marks the pane unavailable
   and the beat degrades, which is the behaviour PROJECT.md requires and the
   reason roles exist.
4. Attach the resolved `params` to the `ModelSource`.

`sources.available_sources` keeps its signature and becomes the fallback path.
`API_ORDER` survives only as display order in the console.

---

## 2. Precedence

    run-block pane  >  profile demos.<demo_id>  >  profile defaults  >  provider default

Enforced in `runs.bind_panes`, in that order, and **tested** — this is the rule
that protects the demos from the configuration. Concretely: `run-blocks.json`
states `temperature: 1.0` on all four panes of `m1-p1`, so no profile can lower
it. When `m2-p2` gets a run block stating a thinking budget, the same protection
applies to the budget, and the profile's `params.think` for `m2` stops having an
effect — correctly, because at that point the budget is what D2 teaches.

A profile parameter the run block also states is not an error and not a silent
loss. It is reported: `GET /console/preflight` returns, per demo, the parameters
the profile sets that a run block will override.

### `teaches_params`

A run block declares the parameters the beat exists to expose:

```json
"m1-p1": { "teaches_params": ["temperature"], "panes": [...] }
```

It does two jobs. It decides what the collapsed pane shows (§6), and it is the
subject of the pre-flight capability check (§5.4). Absent or empty is legal and
means "nothing to foreground" — the safe default, everything behind Info.

A value here must be a name from §3. `tests/test_run_blocks.py` fails otherwise.

---

## 3. Banco's parameter vocabulary

Four names, translated per provider by the adapter in §4. Nothing else crosses
the boundary.

| Banco | Meaning | Type |
|---|---|---|
| `temperature` | sampling temperature | float 0.0–1.0 |
| `max_tokens` | ceiling on what the model may generate for this turn | int |
| `system` | system prompt, sent as a system message/instruction | str |
| `think` | deliberation budget | `false`, `"low"/"medium"/"high"/"max"`, or an int token budget |

`think` is deliberately one field with three shapes, because the vendors do not
agree and D2's mechanism is that deliberation is a *budget*, not a switch. The
adapter translates; where a translation is lossy it is **reported as lossy**,
not silently approximated. An int budget handed to a provider that only takes
levels is dropped with a reason — it is not rounded to `"high"`, because a
rounded budget on a projected screen is the false statement this whole design
exists to prevent.

Pedagogical consequence, worth knowing before D2 is staged: of the four sources,
only Anthropic and Ollama express deliberation as something other than a level —
Anthropic as an explicit token budget, Ollama as booleans *or* levels. If D2's
claim is "a budget, not a switch", the pane that carries the claim should be one
of those two.

---

## 4. Provider layer

### 4.1 The request is built before it is sent

Add to `app/llm/base.py`:

```python
@dataclass(frozen=True, slots=True)
class ProviderRequest:
    model: str
    payload: dict          # exactly what goes to the SDK
    sent: dict             # Banco-vocabulary params that reached payload
    dropped: dict[str, str]  # Banco param -> why it did not
```

`LLMProvider` gains `prepare(messages, params) -> ProviderRequest`, and
`generate` / `generate_stream` take a `ProviderRequest`. No network in
`prepare`, so every provider's parameter handling becomes unit-testable without
a key — which is how `anthropic==1.2.0` dropping `temperature` from
`Messages.create` should have been caught, per that module's own docstring.

`sent` and `dropped` are what the runner emits (§6). They are derived from
`payload`, never from a table.

`redact()` runs over `sent` before it leaves the process. `payload` never
leaves; it is not serialised to any surface.

### 4.2 Per-provider mapping

Verified against vendor documentation on 2026-09-12; every one of these has
changed at least once during this project's life, so the adapter checks the
installed SDK where it can (as `_sdk_accepts_temperature` already does) and
reports a drop where it cannot.

**Anthropic** — `thinking={"type": "enabled", "budget_tokens": N}` on
`messages.create`. `budget_tokens` minimum 1024; the API rejects less. Thinking
tokens count toward `max_tokens`, so `budget_tokens` must be **strictly less
than** `max_tokens` and must leave room for an answer. The budget is a target,
not a hard cap. `think` as a level → drop with reason, or map to a documented
budget only if that mapping is written into the profile by a human, never
invented here. `temperature`: existing `temperature_is_applied` gate, unchanged,
now expressed as a `dropped` entry.

**OpenAI** — reasoning effort is `reasoning_effort` on Chat Completions and
`reasoning.effort` on the Responses API; documented values `none`, `minimal`,
`low`, `medium`, `high`, `xhigh`, `max`, model-dependent. OpenAI's own guidance
is that reasoning models belong on the Responses API, which uses
`max_output_tokens` rather than `max_tokens`.

> **Decided 2026-09-12, and neither of the two ways out was needed.** The
> question was how to make a reasoning model selectable when
> `OpenAIProvider` calls `chat.completions.create(max_tokens=…, temperature=…)`,
> which sends such a model parameters it does not take. The options on the
> table were a Responses-API path or excluding reasoning models from the
> console's list.
>
> Neither: the pinned SDK's `chat.completions.create` already accepts
> `reasoning_effort` **and** `max_completion_tokens`. Checked against
> `openai==3.6.0`, the version both locks pin, by inspecting the signature —
> all four are present. So a reasoning model is selectable on the endpoint
> Banco already uses, and `prepare()` translates:
>
> - `think` as a level → `reasoning_effort`; as a token budget → dropped
>   (`drop.think.openai_takes_a_level`), never rounded to a level.
> - `max_tokens` → `max_completion_tokens` on a reasoning model, `max_tokens`
>   otherwise.
> - `temperature` on a reasoning model → dropped
>   (`drop.temperature.reasoning_model`). D1 is the temperature demo; a pane
>   claiming a temperature it never sent is the failure this whole layer exists
>   to prevent.
>
> The signature is **inspected, not assumed** (`_completions_parameters`), so an
> SDK that removes either field degrades to a reported drop rather than a
> `TypeError` at call time — which is exactly how `anthropic==1.2.0` losing
> `temperature` should have failed and did not.
>
> One thing this does not settle: which model ids count as reasoning models.
> `_REASONING_MODEL` is a pattern, and §4.3 says a capability table is allowed
> to be wrong. When it is, the API refuses the call and the pane narrates the
> refusal — recoverable. `POST /console/check` (§5.3) is what turns that into a
> pre-flight warning rather than a surprise.

**Google** — the shape changed generation to generation: `thinking_config` /
`thinking_budget` in the 2.5 line, `thinking_level` (`low`/`medium`/`high`) in
the 3.x line, carried on the generation config. The adapter must not assume
which one the installed `google-genai` and the selected model accept; it
inspects the `types` module for the field and drops with a reason when absent.
An int budget on a level-only model is dropped, per §3.

**Ollama** — `think` at the top level of `/api/chat`, accepting `true`/`false`
or `"low"`/`"medium"`/`"high"`/`"max"`; some models (GPT-OSS) require a level
and reject booleans. `max_tokens` → `options.num_predict`, already implemented.
`system` → a system message, already handled by `_to_ollama_messages`.

### 4.3 Capability table — advisory only

`app/llm/capabilities.py`: `(provider, model-pattern) -> {param: shape}`,
consulted **only** by the console to decide which control to render and which
shape it takes. It is allowed to be wrong. When it is, the control is offered,
the parameter is dropped at `prepare`, and pre-flight says so. It is never read
by the runner and never reaches a pane event.

---

## 5. Console

### 5.1 Model lists, with provenance

```
GET  /console/models                  -> {provider: {models, source, fetched_at, error?}}
GET  /console/models?provider=google
POST /console/models/refresh          -> model_catalog.clear_cache(), then re-discover
```

`source` is `"live"` or `"fallback"` and is **mandatory in the payload and on
screen**. `model_catalog` already tracks it (`_CacheEntry.live`, `cached()`,
`is_live()`); nothing surfaces it. Today `_models_hint` prints up to eight ids
after a 404 with no indication that they may be the June-2026 static list — a
trainer reading `FALLBACK_MODELS` as an API answer is the same class of error
as a temperature that was never sent. Fix `_models_hint` in the same change:
use `model_catalog.cached()` and label the list.

Ollama models keep coming from `preflight.ollama()` (`/api/tags`), which is
already live-only.

### 5.2 Session profiles

```
GET  /console/sessions                -> [{name, active, updated, note}]
GET  /console/sessions/{name}         -> the profile
PUT  /console/sessions/{name}         -> validate + write (422 on unknown demo id,
                                         unknown role, unknown param, or a key field)
POST /console/sessions/{name}/activate-> SESSION_PROFILE=<name> in .env
DELETE /console/sessions/{name}       -> refuse if active
```

All behind `ConsoleAuth`, all accepting `lang`, like every existing console
route.

UI: a **Binding** card above *Fonti modello*, showing the three roles, each with
a provider select, a model select filled from §5.1 with its provenance badge,
and the parameter controls the capability table allows. Below it, an
**Avanzate** disclosure listing D1–D5, each collapsed and each able to rebind a
role for that module. Per the answer given on 2026-09-12, both live at
pre-flight; neither is reachable while a beat is running.

New strings go in `app/i18n.py` and both `strings.{it,en}.js` in the same
commit, or `tests/test_i18n.py` fails — AGENTS.md rule 9.

### 5.3 Pre-flight checks the configuration, not just the key

`POST /console/check` today sends `"ping"` with default parameters. It should
send the active profile's parameters for each bound source and report
`sent` / `dropped` per role, so the answer moves from *does this key work* to
*does this configuration work*. A dropped parameter is a warning line, not a
failure — the run is still honest, the pane will just say so.

Add to `GET /console/preflight`:

- the active profile name, and per demo the effective binding;
- any profile parameter a run block will override (§2);
- any `demos` key that is not a real demo id.

### 5.4 The capability check per demo

For each demo, for each parameter in any of its beats' `teaches_params`: does at
least one bound pane's `(provider, model)` actually apply it?

Two layers, because they answer with different authority:

- **On page load**, from the capability table (§4.3). Fast, free, advisory. A
  miss renders as a warning naming the demo, the parameter, and which configured
  sources *would* apply it — so the fix is one select away.
- **On `POST /console/check`**, from a real call carrying that parameter, reading
  `dropped` back. Slow, costs a call per source, and is the answer that counts.

A demo whose only temperature knob is bound to a model that discards temperature
runs, looks correct and teaches nothing. This check is the thing that catches it
before the room does — it is the pre-flight equivalent of `temperature_is_applied`.

Not a hard failure: a trainer may knowingly rehearse a demo on a model that
ignores the knob. It is a warning that names what will be lost.

---

## 6. Runner and harness

`_pane_payload` gains `sent` and `dropped` and keeps everything it has.
`temperature_applies` stays for one release as a derived alias
(`"temperature" not in dropped`) so the harness page can change separately, then
goes.

`sent` is known before the call, so it rides the existing `plan` event — the
harness lays out its panes before any text arrives and must be able to label
them then.

Harness rendering. Cleared under AGENTS.md section 7 on 2026-09-12, in the shape
below and no wider.

**Collapsed pane** — the permanent state:

- pane label, model id, egress. The egress chip is outside the Info mechanism
  and never collapses: invariant 4 needs the room to have watched calls leave
  before D5-A turns the network off.
- plus every parameter in the beat's `teaches_params`, rendered from `sent` /
  `dropped`. `m1-p1` declares `temperature`, so D1's four panes show `1.0` with
  no gesture; D3 declares nothing about sampling and carries no temperature for
  the room to ignore.
- a parameter that is in `teaches_params` and in `dropped` renders as the caveat,
  not as the value: *"temperatura 1.0 — non applicata da questo modello"*. This
  is what `temperature_ignored` already does; it generalises.

**Info** — one toggle in the harness header, expanding the parameter strip on
**all panes at once**. A room comparing panes needs them in step, so a per-pane
"?" is the secondary control, not the primary one. State in `localStorage`
(`banco.info`), per browser, like `banco.lang` — the console must not be able to
expand the projector.

Expanded adds: the remaining `sent` parameters, every `dropped` entry with its
reason, and per-pane token counts once [ADR 0005](../adr/0005-usage-is-measured-headroom-is-not-credit.md)
lands. The system prompt as sent and the full prompt as sent are long text and
stay on the per-pane click.

Collapsed is silent, not vague: a pane not showing a parameter makes no claim
about it. That is what makes hiding safe, and it is why a stale or unqualified
value is the one thing that may never render.

---

## 7. Ceilings

Removed, not raised — see [ADR 0005](../adr/0005-usage-is-measured-headroom-is-not-credit.md)
and [its spec](usage-and-headroom.md). `HARD_MAX_TOKENS` goes;
`Settings.max_tokens` loses its `le=4000` bound and becomes the default for a
role whose profile entry states no `max_tokens`; `daily_token_budget` stops
refusing. The only thing this spec needs from that one is that
`prepare()` may emit a `max_tokens` of any size, and that an Anthropic request
combining `think` and `max_tokens` validates `1024 <= budget < max_tokens`
locally and drops with a reason rather than letting the API reject the call.

---

## 8. Tests

Additions to the existing suite, in its style:

- `test_sessions.py` — merge order per role; a demo override rebinding one role
  leaves the others on defaults; an unknown demo id or role fails validation; a
  profile containing anything key-shaped is rejected; a missing or corrupt
  profile falls back to the derived binding.
- `test_precedence.py` — a profile cannot change a run-block-stated
  `temperature`; `m1-p1` plans at 1.0 on all four panes under every profile in
  `demo/sessions/`. **This is the test that protects the demos.**
- per-provider `prepare` tests, no network: `sent` and `dropped` for each of the
  four parameters on each of the four providers, including the level-vs-budget
  mismatch and the Anthropic `budget_tokens >= max_tokens` rejection.
- `test_harness_invariants.py` — no `sent` payload, on any path, contains a
  credential or anything key-shaped; `redact` covers it.
- `test_run_blocks.py` — every `demos` key in every shipped profile is a demo id
  that exists; every `teaches_params` value is a name from §3.
- `test_capability_check.py` — a demo declaring `temperature`, bound to a model
  that drops it, produces exactly one pre-flight warning naming the demo, the
  parameter and an alternative source.
- harness rendering — a parameter in `teaches_params` and in `dropped` renders
  as the caveat, never as a bare value; a pane shows no parameter that is
  neither in `teaches_params` nor revealed by Info.
- `test_i18n.py` — new console strings in both catalogues, as always.

Clean-checkout verification per AGENTS.md §3 before this is accepted. Not in the
existing `venv/`.

---

## 9. Order of work

1. ~~`prepare` / `ProviderRequest` on the four providers, plus their tests.~~
   **Done 2026-09-12.** `tests/test_provider_requests.py`, 30 tests, no network
   and no key. Two defects surfaced while building it, both recorded in the
   CHANGELOG: the Google provider tests had been red on every clean checkout
   since `automatic_function_calling` was added, and
   `test_a_model_that_ignores_temperature_is_reported_as_such` asserted the
   opposite of what the pinned SDK does.
2. ~~Ceilings (§7).~~ **Done 2026-09-12.** `HARD_MAX_TOKENS` gone,
   `Settings.max_tokens` unbounded above, the daily budget measured and no
   longer enforcing.
3. ~~`sessions.py`, the profile schema, resolution and precedence, plus tests.~~
   **Done 2026-09-12.** `tests/test_sessions.py` and `tests/test_precedence.py`.
   `SESSION_PROFILE` in `.env` selects a profile; there is still no UI.
4. ~~The `_models_hint` fix.~~ **Done 2026-09-12** — the hint now says whether
   the list came from the API or from the static backstop.
   `GET /console/models` with provenance is still to do.
5. `teaches_params` in `run-blocks.json` — **the field and its tests are done**
   (`m1-p1` and `m1-p2` declare `temperature`); the capability check (§5.4) is
   still to do.
6. Console UI: binding card, then *Avanzate*.
7. `sent` / `dropped` on the pane event — **the server half is done**; the
   harness rendering and the Info reveal (§6) are still to do.
8. `think` end to end, which is what unblocks `m2-p2`. The provider half is
   done; what remains is a run block for `m2-p2` and a way to choose the budget.

Steps 1–5 are invisible to the room and reversible. Step 7 is the one that
changes what a client sees.
