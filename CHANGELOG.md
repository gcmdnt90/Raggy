# Changelog

## Unreleased

**Italian reaches the model, not only the screen.** The language work in
September translated everything Banco *renders*. It did not translate three
things Banco *sends*, and each of them is invisible until the one run where it
is not.

- **The system prompt was English only.** `knowledge_base/prompts/system_chatbot.yaml`
  now carries `prompt` and `prompt_it`, the same `<field>` / `<field>_it`
  convention as the demo database and `run-blocks.json`, read by the same
  `app.i18n.localized`. `PromptManager.get_chatbot_system_prompt(language)` and
  `save_prompt(..., language)` follow; editing the Italian prompt no longer
  overwrites the English one, because the two are separate texts sent to a
  model rather than a translation pair anyone maintains at runtime.
- **It said "Always reply in the user's language", which is inference, not
  instruction.** Each prompt now *states* its output language. A frontier model
  infers correctly; the 4B-class local model D5-A runs on frequently does not,
  and answers in English. **D5-A's entire claim is that only the writer
  changed** — same index, same retrieved passages, generation moved to the
  local model — so a language difference Banco caused would be read by the room
  as something the local model did. This is also a prerequisite for D3: the
  system prompt is what governs rungs 2 and 3, and objective 2 puts it on the
  projected surface *as sent*.
- **The conversation summariser was English only**, and its output is written
  back as conversation history. An Italian conversation would turn English a
  few turns in, looking like the model drifting rather than like Banco doing
  it. So was the `KNOWLEDGE BASE CONTEXT:` heading Banco inserts into the
  system prompt above the retrieved passages — a seam in the middle of a text
  that gets projected.
- **The chain files carried no language, and the chain is five files handed
  from one demo to the next.** Nothing stopped a trainer rehearsing D1 in
  English and delivering D2 in Italian, at which point `d1-bozze.md` holds
  English drafts and D2's Italian prompt says "queste quattro bozze" directly
  above them. Every part is correct and the material is wrong. `write_chain_file`
  now stamps `<!-- banco:lang=it -->` first in the file; `runs.chain_file_language`
  reads it back, `runs.language_mismatches` reports it on the `plan` event, and
  pre-flight names the offending files and what to do. **Reported, never
  refused** — invariant 3 says the chain never waits, so the beat still runs and
  the material is still pasted. A shipped fallback carries no marker and makes
  no claim: `None` means "unknown", never "English", or every fresh install
  would warn.
- A session profile's `note` is read aloud at pre-flight and shown on the
  console, so it is a string Banco *carries*: `note` / `note_it`.

`tests/test_italian_coverage.py` is the guard. It fails on a catalogue entry
missing either language, on an entry whose two languages are the same string, on
a system prompt that does not state its output language, on a run block whose
`teaches` or pane label has no Italian, on a beat that sends identical text in
both languages, and on a shipped profile note with no `note_it`.

**D2 runs.** `m2-p1` and `m2-p2` have run blocks and have left `_unblocked`.
Banco now executes four of the twenty active beats instead of two.

- **`m2-p1` — two judges, one pasted input.** D2 inverts D1's shape: one input
  to two panes, to show them differing in *depth*, where D1 gives one input to
  four panes to show them disagreeing. The pane labels are deliberately neutral,
  "Giudice A" and "Giudice B" — never "small" and "large". Which is which is a
  property of the session profile, not of `run-blocks.json`, and a pane
  captioned "modello piccolo" beside whatever a profile happened to bind is a
  false statement on a projected screen. The model id carries the fact instead,
  and it is true by construction.
- **`m2-p2` — the budget.** Both panes ask the *same role*, so both bind to the
  same provider and model, and the only difference between them is the reasoning
  budget: `think: false` against `think: 4096`. Two models here would show
  capability again, which beat 1 already showed. The budget is stated as an
  integer because that is the claim D2 makes — deliberation is a budget, not a
  switch — and `max_tokens: 8000` is stated alongside it because a budget has to
  fit under the ceiling, which makes the ceiling part of what the beat asks for
  rather than a detail of the configuration.
- **An input with no placeholder is appended, not silently dropped.** Both D2
  beats name `demo/catena/d1-bozze.md` and neither prompt has a `[PASTE …]`
  hole: they say "these four drafts" and expect them to be in the conversation,
  because in the room a person pastes them under the question. `build_prompt`
  now supports `append: true` for exactly that, and `tests/test_i18n.py` checks
  in both languages that the file actually arrives — the failure mode otherwise
  is a model asked to compare four drafts it was never given, which reads on
  screen as a plausible answer.

### Two judges on one provider were being called a degraded run

`requires_sources` counted distinct **providers**. D2's whole configuration is
two sizes of one model family — `qwen3:8b` against `qwen3:1.7b`, or a frontier
model against a small local one — and on one provider that counted as one
source, so the beat was marked degraded and announced a replay it did not need.
It now counts distinct `(provider, model)` pairs, which is also the right
measure for D1, whose own note says the beat teaches that "two models disagree
with each other".

### The capability check, so D2 cannot fail quietly

A demo bound to a model that discards its own knob runs, fills its panes, reads
correctly on a projector and teaches nothing. Nothing in pre-flight caught that:
the key works, the model answers, the beat completes.

`preflight.capability_warnings` now asks, for every parameter a beat declares in
`teaches_params`, whether any bound pane would actually send it — and names a
configured source that would, so the fix is one select away. It is the
generalisation of `temperature_is_applied`, which was the one rule that existed
for one parameter.

It is answered by **building the request**, not by consulting a table.
`prepare()` is pure and touches no client, so `LLMProvider.for_inspection`
constructs a provider with no credential and no client at all and asks it. The
same code that decides what reaches the API decides what pre-flight promises
about it; a capability table would be a second source of truth able to disagree
with the first. It costs nothing and runs on page load.

Concretely, for D2's budget: **Anthropic and Google carry it, OpenAI and Ollama
do not** — they take levels, and a level is not a budget, so the parameter is
dropped with a reason rather than rounded. `demo/sessions/esempio.json` rebinds
only `secondary` for D2, leaving `primary` on the API default, for that reason.

Advisory, never a hard failure: a trainer may knowingly rehearse on a model that
ignores the knob. What it may not do is stay silent.

**The spine of model control, steps 1–4 of `docs/specs/model-control.md`.**
Nothing on the projected surface changes yet. What changes is that a parameter
can now be *sent* and *said to have been sent*, which is what D2 and D4 have
been waiting for.

- **`prepare()` and `ProviderRequest` on all four providers.** Each adapter now
  builds its request in an inspectable step before the call and reports two
  things: the Banco-vocabulary parameters that reached the payload (`sent`) and
  the ones that did not, with a reason (`dropped`). No network, no credential,
  so `tests/test_provider_requests.py` — 30 tests — asserts every provider's
  parameter handling without a key. `temperature_is_applied` stops being the
  one parameter with a rule and becomes a case of a general one.
- **`Pane.thinking` now actually reaches the API.** It was declared in the
  schema, carried onto the pane and emitted to the harness, and no provider
  accepted it — the same defect as the temperature, one layer along. It is now
  `think` in Banco's vocabulary, one field with three shapes because the
  vendors do not agree: `false`, a level, or a token budget. Anthropic gets a
  `budget_tokens`, Ollama a boolean or a level, OpenAI a `reasoning_effort`,
  Google whichever of `thinking_budget` / `thinking_level` the installed SDK
  and the chosen model actually has. **A shape a provider cannot take is
  dropped with a reason, never approximated** — a budget rounded to "high" on a
  projected screen is the false statement this layer exists to prevent.
- **The ceilings are gone, not raised** (ADR 0005). `HARD_MAX_TOKENS = 4000`
  clamped every request in `app/llm/router.py`, and `Settings.max_tokens` was
  bounded `le=4000`. Between them they made an Anthropic thinking budget
  *arithmetically impossible*: the budget must be at least 1024 and strictly
  below `max_tokens`, so the smallest legal budget left under 3000 tokens for an
  answer and every larger one was unreachable. The daily token budget also
  stopped refusing calls — it refused on a character-count *estimate*, so a
  demonstration could stop mid-lesson for a number that was neither true nor
  visible to anyone in the room. Usage is still measured on every call.
- **Session profiles** (`demo/sessions/<name>.json`, ADR 0004). A named file
  binds each role to a provider, model and parameters, with per-demo overrides
  that merge *per role*. `SESSION_PROFILE` in `.env` selects one; no profile, a
  missing file or an unparseable one all fall back to the derived binding, so an
  existing install is unaffected and a corrupt profile cannot cancel a lesson.
  A profile carrying anything key-shaped is refused whole. A role whose source
  is unreachable **stays dropped** and its panes go unavailable — it never
  slides onto another provider, because showing the room four working panes
  would teach the wrong lesson about what their own configuration can do.
  This is what lets D2 bind two sizes of the same model family, which no
  positional rule could express.
- **Precedence is enforced and tested**: run-block pane > `demos.<id>` >
  `defaults` > provider default. `tests/test_precedence.py` runs against every
  file in `demo/sessions/` and fails if one moves D1 off temperature 1.0. That
  is the test that protects the demonstrations from the configuration — without
  it a profile could quietly converge D1's four drafts and leave a beat that
  runs, reads correctly and shows nothing.
- **`_models_hint` says where its list came from.** It printed up to eight model
  ids after a 404 with no indication whether they were the API's answer or
  `FALLBACK_MODELS`, a static list last verified in June 2026. A trainer acting
  on a stale list picks a model the API will refuse, while fixing the error that
  produced the hint. `model_catalog` always knew; nothing surfaced it.
- **The OpenAI question in the spec is closed, and neither proposed answer was
  needed.** `openai==3.6.0` — the pinned version — already accepts
  `reasoning_effort` and `max_completion_tokens` on `chat.completions.create`,
  so reasoning models are selectable without a Responses-API path and without
  excluding them from the console's list. The signature is inspected rather
  than assumed, so an SDK that drops either field degrades to a reported drop.

### Two defects the suite was carrying

Both were found by running `pytest` against `requirements.lock` in a scratch
virtualenv, per AGENTS.md §3. Neither would appear in an existing `venv/`, which
is the same way the two 2026-09-05 defects survived.

- **`tests/test_google_provider.py` had been red on every clean checkout** since
  `automatic_function_calling` was added to `app/llm/providers/google.py`. The
  test's `_Types` double does not have `AutomaticFunctionCallingConfig`, so ten
  tests died with `AttributeError` before asserting anything. The provider now
  sets that field only when the installed SDK has it, which fixes the tests and
  is also correct: the field does not exist in every `google-genai` release.
- **`test_a_model_that_ignores_temperature_is_reported_as_such` asserted the
  opposite of the truth.** It required
  `temperature_applies("anthropic", "claude-sonnet-4-6")` to be `True`, but
  `anthropic==1.2.0` — pinned in both locks — has no `temperature` on
  `Messages.create`, which the provider module's own docstring explains at
  length. **On a clean checkout no Anthropic pane sends a temperature at all,
  and D1 is the temperature demo.** The test now asserts the model rule and the
  SDK rule separately and requires the displayed answer to be their conjunction,
  and a new test proves the parameter shows up in `dropped` with a reason rather
  than silently vanishing. The underlying situation is unchanged and is a
  configuration question, not a code one: D1 needs at least one pane on a source
  that carries temperature.

**The demo database is client-agnostic, and now provably.** `sectors[].client`
is the substitution map, so anything written there reaches the projected
surface. `sectors[numismatics].client.name` held a real client's name — from
the first delivery until 2026-09-12 — and although no prompt used `{{name}}`,
the deck inlined it into every published `index.html`. It is now empty on every
sector.

- `tests/test_harness_invariants.py` gains `test_no_sector_declares_a_client_name`,
  which fails if a name comes back. Two existing guard tests looked for a real
  name in the database and **skipped themselves** once there was none to find —
  they now run against a synthetic client, so the guard is exercised whatever
  the database declares. Added `test_an_empty_client_name_does_not_match_everything`:
  an empty name must be a no-op in `_assert_no_client_name`, not a substring
  that refuses every demo.
- Operators on the synthetic sheets are **invented initials, not surnames**. The
  previous names were drawn from the commonest San Marino surnames and one of
  them matched a sitting trade-association president — indistinguishable, on a
  projected sheet, from real data about a real person.

**Sector packs caught up with the deck: `defi`, `associazione`, `maglieria`.**
The vendored `demo/demo-prompts.json` and `demo/kit/` were at their 2026-09-02
state, three sectors behind. `demo/demo-prompts.json` is re-vendored
byte-identical (deck version 7); `demo/kit/` is re-synced whole. `demo/data/`
must be regenerated for all six sectors — see `demo/kit/README.md`.

`maglieria` is a production-software house for knitwear: the record is a
**scheda di specifica** and the invented scale is **SP-1 … SP-5**, which
measures how much specification a request is still missing and who must sign
it — not priority and not size. Its SP-5 level says the request must not become
a ticket at all, which no priority framework expresses and no ungrounded model
can guess.

No run block changed: Banco still executes `m1-p1` and `m1-p2`, and every other
active beat stays in `_unblocked`. The new sector's variants carry the same
`[PASTE RAW NOTES]` / `[INCOLLA APPUNTI GREZZI]` placeholders the run block
substitutes, in both languages.

**Banco speaks Italian.** Italian is the default on both surfaces; English is
one control away, on every screen.

- **A language switch on the harness and on the stage console**, per browser
  rather than per server. It lives in `localStorage` and travels to the server
  as a `lang` parameter on each request, so the console can be in English while
  the projector stays in Italian — which is the case that matters, because the
  two are routinely open at once on two screens. Putting a new control on the
  projected surface was checked first, per AGENTS.md section 7.
- **`app/i18n.py` rewritten.** It held `_ui_language` as module state, inherited
  from a single-user Streamlit app that no longer exists here, and a catalogue
  of about a hundred Raggy strings — chat, knowledge base, admin panel, setup
  wizard — that no surface in this repository reads. One process-wide language
  serving two surfaces is the bug it would have caused. It is now `t(key, lang)`
  plus `localized(node, field, lang)`, which is the only code that knows the
  database's `<field>_it` convention.
- **The pasted file was not reaching the model in Italian.** `run-blocks.json`
  substituted `[PASTE RAW NOTES]`, but the Italian prompt for m1-p1 says
  `[INCOLLA APPUNTI GREZZI]` — so an Italian run sent the model the literal
  placeholder instead of the raw notes, and the room would have watched four
  panes answer a question with nothing in it. The placeholder is part of the
  prompt, so it is translated too: `replaces` / `replaces_it`, checked for every
  input in both languages by `tests/test_i18n.py`.
- `demo/run-blocks.json` gains `teaches_it`, a `label_it` per pane, and
  `_unblocked_it` — the refusal reason beside a beat the trainer cannot run is
  rendered on the projected surface, so it is translated like everything else
  there. `demo/demo-prompts.json` is untouched: it is vendored from the deck at
  the pin in `DECK-PIN.txt` and was already bilingual.
- Pre-flight, the console's replies, the run refusals and the Ollama address
  validation are written in the language the browser asked for. A provider's own
  error message is inserted, never rewritten — it is evidence.
- The handover file a successful run writes carries its header in the language
  the beat ran in. D2 opens that file in front of the room.
- `app/rag/pipeline.py` was the last reader of the old process-wide language and
  took the untrusted-data clause from it inside a bare `except`; it now takes a
  `language` argument, so the failure is a caller's to see rather than a silent
  fallback to English.
- `tests/test_i18n.py`: both catalogues hold the same keys and the same
  placeholders, every surface loads them and offers the switch, the demo
  database is translated where the room reads it, and planning in English does
  not change the next Italian plan.

---

Credential hygiene, and the defects in the Control Room visual pass.

- **Provider errors no longer carry credentials to a screen or a log.**
  `app/utils/redact.py` scrubs a configured key by exact value and anything
  key-shaped by pattern; `runner`, `preflight` and the console error paths call
  it, and a `RedactingFilter` on both log handlers covers `logger.exception`.
  The path that mattered: `google-genai` authenticates with the key as a
  `?key=` query parameter and stringifies `APIError` as
  `f"{code} {status}. {details}"` where `details` is the raw response body, so
  a transport failure put the key in a `pane_failed` event — which the harness
  prints on the projected surface. OpenAI's 401 echoes a partially masked key,
  and a fragment on a projected screen is still a fragment. SECURITY.md had
  promised both properties since the fork; nothing enforced either.
- **The Google provider ran against a package this project does not ship.**
  It imported `google.generativeai` while `pyproject.toml` and both locks pin
  `google-genai`. On a clean checkout a configured Google key produced a pane
  that failed with "Package 'google-generativeai' not installed", naming a
  non-dependency; `scripts/setup_wizard.py` had the same import inside a
  blanket `except`, so it reported a working key as invalid. Ported to the
  client API, with `tests/test_google_provider.py` — there had been no test.
- **`[hidden]` is honoured again on the projected surface.** `.chip` sets
  `display: inline-flex`, which outranks the user-agent rule, so `#mode` — the
  LIVE/REPLAY indicator — sat on screen as an empty pill before every run.
- **Pane grouping stopped borrowing semantic colours.** The A/B pair marker
  used `--replay` for panes 3 and 4, so half of every live run was outlined in
  the colour reserved for a recording, and `--local` for panes calling a vendor
  endpoint. It now uses `--pair-a` / `--pair-b`, which mean nothing else.
- The stage console's sidebar marks the section actually in view; it had a
  static `active` class that never moved. Cards carry `scroll-margin-top` so an
  anchor does not land under the sticky bar, and the page has one `<h1>`.
- A console password containing a non-ASCII character returned 500 rather than
  authenticating: `secrets.compare_digest` rejects non-ASCII `str`. Compared as
  bytes now, so an accented password works.
- A value containing a newline can no longer define a second variable in
  `.env`. Refused in `save_settings_to_env` for every caller, and as a 422 at
  the console's request model.
- Demo id, shape and beat id are HTML-escaped in the harness like every other
  interpolated field.
- **The live check said "did not answer" and nothing else.** It went through
  `router.test_connection()`, and every provider's implementation catches all
  exceptions and returns `False` — so the reason (wrong key, retired model, no
  network, budget spent) was discarded inside the provider before pre-flight
  could see it. The one check that exists to tell a working key from a stored
  one now calls `generate` directly and reports the redacted exception.
- **A third configured key was never checked.** There are two API roles and
  three possible keys, and `live_checks` iterated only the sources bound to a
  pane — so with Anthropic, OpenAI and Google all set, Google was silently
  absent from pre-flight. Bound sources keep their role as the report key; a
  configured provider with no pane is now reported under its own name.
- **Logging was never configured.** `setup_logging` had no caller, so there was
  no `logs/raggy.log` to diagnose from, the retention sweep never ran, and the
  redacting filter was never attached. Both now run from the app's lifespan.
- **An edited stylesheet did not necessarily reach the browser.** Neither
  `StaticFiles` nor `FileResponse` sends `Cache-Control`, so a browser could
  apply heuristic freshness and reuse the previous design after a restart. Both
  surfaces and `/static/` now send `no-cache`, which is revalidate-every-time
  rather than don't-store: the ETag still answers 304.
- Removed the marketing register from the stage console ("Before the room
  arrives", "Everything in one glance."). The heading is `Pre-flight`, the
  readiness card is `Readiness`.

Then, with pre-flight finally able to report a reason, three real failures it
had been hiding:

- **Every Anthropic pane died before the request was made.**
  `Messages.create()` in `anthropic==1.2.0` — the version both locks pin — has
  no `temperature` parameter and no `**kwargs` to absorb one, so passing it
  raised `TypeError: Messages.create() got an unexpected keyword argument
  'temperature'`. The old gate asked only whether the *model* honours sampling
  parameters; the SDK is a second gate and it is currently shut for every
  model. `_sdk_accepts_temperature` now inspects the installed signature —
  so an SDK that brings the parameter back needs no edit, and an inspection
  that fails resolves to "do not send it", which fails safe.
  `sources.temperature_applies` consults the same combined rule, so the
  projected surface says "temp 0.3 not sent" instead of claiming a temperature
  that never left the machine (PROJECT.md invariant 2).
- **The Google default model had been retired.** `gemini-2.5-flash` answers
  404 "no longer available to new users … please update your code to use
  models/gemini-3.6-flash". Default and fallback list updated to the id
  Google's own error named, not a guess.
- **Model ids rot, so a 404 now names the alternatives.** Pre-flight appends
  the provider's live model list to `LLMModelNotFoundError` — the difference
  between "gemma3:4b not found" and "gemma3:4b not found. Available:
  qwen3:8b, …" is the difference between a search engine and a fix. The action
  line is per-provider too: Ollama has no key, so telling a trainer the key was
  stored but not working sent them looking for a credential that does not exist.
- Disabled the Gen AI SDK's automatic function calling. Banco sends no tools,
  but the SDK enables AFC by default and logs a WARNING on every call telling
  the caller to use `Chat.send_message` — noise in the one log read during a
  failure.
- Both surfaces carry an inline favicon; `/favicon.ico` had been a 404 per load
  and a broken tab icon. The Google key field hints at both key shapes.

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
