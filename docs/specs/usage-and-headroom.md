# Usage and headroom — implementation spec

Implements [ADR 0005](../adr/0005-usage-is-measured-headroom-is-not-credit.md).
Companion to [model-control.md](model-control.md), which owns model binding and
parameters.

Two claims this spec has to make true: a token count Banco shows is one a
provider reported, and a number about the trainer's account never reaches the
projector.

---

## 1. Remove the ceilings

| File | Change |
|---|---|
| `app/llm/router.py` | delete `HARD_MAX_TOKENS` and `_effective_max_tokens`'s clamp; `DEFAULT_MAX_TOKENS` stays as the value used when nothing states one |
| `app/llm/router.py` | delete `_ensure_budget` and the `LLMBudgetExceededError` raise from both `generate` and `generate_stream` |
| `app/config.py` | `max_tokens: int = Field(default=1500, ge=512)` — lower bound only |
| `app/config.py` | `daily_token_budget` → rename to `daily_token_note` or keep the name and stop reading it as a gate; it becomes a figure pre-flight reports against, not a limit |
| `app/llm/base.py` | `LLMBudgetExceededError` retires — leave the class for one release so nothing breaks on import, marked deprecated |
| `app/utils/token_budget.py` | `can_spend`, `is_budget_exhausted`, `remaining_budget` go; `record_usage`, `get_daily_usage` and the SQLite table stay |

`logs/tokens.db` holds estimates from before this change and measurements after,
with nothing to tell them apart. It is gitignored scratch: delete it once on
upgrade rather than migrate it.

---

## 2. Measure, do not estimate

The defect: `LLMRouter.generate_stream` records
`estimate_messages_tokens(messages) + estimate_text_tokens(chunks)` — characters
÷ 4 — and never reads provider usage. The runner calls only `generate_stream`.
`usage_from_provider_usage` handles all four providers' shapes correctly and is
reachable only from `generate`, which the demonstration path never touches.

### 2.1 Shape

`generate_stream` stops being `Iterator[str]` and yields a small tagged union, or
— less disruptive, and preferred — keeps yielding text and gains an out-parameter
the provider fills:

```python
@dataclass(slots=True)
class StreamUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    measured: bool = False        # False -> nothing to show, not "zero"
```

`generate_stream(..., usage: StreamUsage | None = None)`. The provider populates
it as the stream terminates; the runner reads it after the loop and puts it on
`pane_done`. A provider that cannot report leaves `measured=False`, and nothing
downstream renders a number.

`measured=False` must never be rendered as `0`. That is the failure this whole
spec exists to prevent, in its most plausible form.

### 2.2 Per provider

Shapes below are the expected ones; **confirm each against the pinned SDK before
relying on it**, and cover it with a test — this is the `anthropic==1.2.0`
lesson, where an assumed signature killed every Anthropic pane.

**Anthropic** — documented: `message_start` carries `usage.input_tokens` and an
initial `output_tokens`; `message_delta` carries a **cumulative**
`usage.output_tokens`. The SDK's `.stream()` context manager also exposes
`get_final_message()`, returning the same `Message` that `.create()` would,
usage included. Prefer `get_final_message()` after the text loop — one call, no
event bookkeeping.

**OpenAI** — Chat Completions omits usage from a stream unless asked. Expected:
`stream_options={"include_usage": True}`, after which a final chunk arrives with
empty `choices` and a populated `usage`. The current loop reads
`chunk.choices[0]` unguarded, so that final chunk would raise `IndexError` —
guard it when adding this. If the Responses API path lands (model-control §4.2),
usage arrives on the completed event instead.

**Google** — `usage_metadata` on the response chunks; the last chunk carries the
final counts. `GoogleProvider._usage` already parses the shape for the
non-streaming path and can be reused as-is.

**Ollama** — already there and thrown away: the `done` chunk carries
`prompt_eval_count` and `eval_count`, and `generate_stream` breaks on
`chunk.get("done")` without reading them. One-line fix, and the only provider
where the data is currently discarded rather than never requested.

### 2.3 Events

`pane_done` gains `usage: {input, output, measured}`. It already fires once per
pane at the end of that pane's stream, which is exactly when the counts are
known, so no new event is needed.

`router.generate` and `router.generate_stream` record the measured figure when
there is one and the estimate otherwise, and `record_usage` gains a flag so the
ledger knows which it stored.

---

## 3. The usage widget

Two pages, arrows left/right, hidable by a button, state in `localStorage`
(`banco.usage.page`, `banco.usage.hidden`) per browser.

### 3.1 Page 1 — tokens. Harness.

This is teaching material, not telemetry, so the layout follows what it teaches.

**Primary: the beat that just ran, per pane, side by side.**

```
m3-p1 · rung        in        out
 nessun documento   890       412
 tutti i documenti  38 400    397
 recuperati         1 520     404
```

Input tokens across panes *is* D3's ladder. The ratio is the lesson, so the
panes must be readable against each other — same units, aligned, no
abbreviation that hides an order of magnitude (`38 400`, never `38k`).

**Secondary, small: the lesson so far**, one line, total per provider.

Not a live-incrementing counter. A number moving during generation pulls the
room's eyes off the output, and the figure that teaches is the one that is
stable at the end of the beat.

A pane whose provider reported nothing shows `—`, never `0`.

### 3.2 Page 2 — headroom. Console.

Per configured provider: requests remaining / limit, input and output tokens
remaining / limit, and the reset time, read from the response headers of the
most recent call and refreshed by `POST /console/check`.

- **Anthropic**: `anthropic-ratelimit-requests-{limit,remaining,reset}`,
  `anthropic-ratelimit-input-tokens-{limit,remaining,reset}`,
  `anthropic-ratelimit-output-tokens-{limit,remaining,reset}`. Remaining token
  values are rounded to the nearest thousand; reset is RFC 3339. Ordinary key.
- **OpenAI**: `x-ratelimit-{limit,remaining,reset}-{requests,tokens}`, plus
  project-scoped variants. Ordinary key.
- **Google**: not exposed. The page says so and links to AI Studio's rate-limit
  view. An absent instrument that says it is absent is honest; a zero is not.
- **Ollama**: local, no limits. The row says so.

Reading headers means reaching the raw response. Both SDKs expose it
(`client.messages.with_raw_response...` / `client.chat.completions.with_raw_response...`
in the current generation) — **verify against the pins**, and where a provider
cannot be made to yield headers, that provider's row degrades to "not available"
rather than the page failing.

Headers are captured opportunistically from calls Banco already makes. Never
spend a call to refresh the widget.

**Nothing about money on either surface.** Cost via Admin APIs is explicitly out
of scope (ADR 0005 decision 4). If it is ever wanted it needs its own ADR,
because it means an organisation-admin credential on the machine that goes to
client sites.

### 3.3 Placement

| | Harness | Console |
|---|---|---|
| Page 1 — tokens | yes | yes (with the cumulative line expanded) |
| Page 2 — headroom | **no** | yes |

The harness widget has one page and no arrows. It is the same component with
page 2 absent, not a second component — and the absence is enforced server-side:
the headroom payload is served from a console route, so the harness cannot
render it even if a client-side condition is wrong.

Hidden by default on the harness; a keyboard shortcut and a small chip to bring
it back.

---

## 4. Endpoints

```
GET /api/usage/last            harness  -> last beat, per pane, measured flags
GET /console/usage             console  -> the above plus today's ledger per provider
GET /console/headroom          console  -> per provider, from cached headers
```

`/api/usage/last` carries no provider account information of any kind — pane
index, model, in, out, measured. Same redaction path as every other harness
payload.

---

## 5. i18n

New strings in `app/i18n.py` and both `strings.{it,en}.js`, same commit, or
`tests/test_i18n.py` fails. Italian first.

Vocabulary: `headroom` is **not** in the do-not-translate list at the head of
`strings.it.js` — that list is for words the lesson teaches (`beat`, `replay`,
`live`, `egress`, `prompt`, `pre-flight`, `harness`, `stage console`). This one
is trainer-facing plumbing, so it reads in Italian: *margine* / *limite residuo*.

---

## 6. Tests

- per provider, `generate_stream` populates `StreamUsage` from a recorded
  terminator fixture — including the OpenAI final chunk with empty `choices`,
  which the current loop would raise on.
- `measured=False` renders as `—` and never as `0`, on both surfaces.
- no harness payload, on any route, contains a rate-limit or account field.
- `/console/headroom` returns "not available" for Google rather than zeros.
- removing the budget gate: a request far above the old `HARD_MAX_TOKENS`
  reaches `prepare()` with its `max_tokens` intact.
- `tests/test_i18n.py` as always.

---

## 7. Order

1. §1, the ceilings. Unblocks the thinking budget in model-control.
2. §2, real usage, per provider with tests. Nothing renders yet.
3. §4 endpoints and §3.1 page 1 on the console, where a wrong number costs
   nothing.
4. Page 1 on the harness.
5. §3.2 headroom, console only.

Steps 1–3 are invisible to the room. Step 4 is the one that changes what a
client sees, and it is covered by the section 7 clearance given on 2026-09-12
together with the Info reveal.
