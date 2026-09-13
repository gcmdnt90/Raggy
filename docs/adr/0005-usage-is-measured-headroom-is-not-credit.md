# 5. Usage is measured, and headroom is not credit

Date: 2026-09-12
Status: Accepted
Related: [0004](0004-session-profiles-bind-roles-to-sources.md)

## Context

Three guards stand between Banco and the API, all inherited from Raggy:
`LLMRouter.HARD_MAX_TOKENS = 4000`, `Settings.max_tokens` bounded `le=4000`, and
`daily_token_budget` defaulting to 200 000 with a hard refusal
(`LLMBudgetExceededError`) when it is spent.

They make sense in Raggy, which has users who are not the key holder. Banco does
not: it is run by the person whose keys it spends, in front of a paying client,
on a clock. A ceiling that refuses mid-beat converts an affordable overspend
into a failed demonstration — the exact outcome this repository exists to
prevent. They also make ADR 0004's thinking budget arithmetically impossible:
Anthropic wants `budget_tokens >= 1024` and strictly below `max_tokens`, so a
4000 ceiling leaves under 3000 tokens for the answer.

Removing a guard without putting an instrument in its place is how a spend is
discovered afterwards. So the guard is replaced by a display — and the display
turns out to have a defect underneath it.

**Every token number Banco holds today is an estimate.**
`LLMRouter.generate_stream` records `estimate_messages_tokens(...) +
estimate_text_tokens(...)`, which is characters ÷ 4. The runner only ever calls
`generate_stream`. `usage_from_provider_usage` exists, handles all four
providers' shapes correctly, and is reachable only from `generate`, which
nothing in the demonstration path calls. `OllamaProvider.generate_stream` breaks
on the `done` chunk without reading `prompt_eval_count` and `eval_count`, which
arrive in that very chunk. So a token count on the projected surface would be a
guess under a label that says measurement — the same class of statement as a
temperature that was never sent, which PROJECT.md objective 2 and
`temperature_is_applied` already forbid.

**Remaining credit is not obtainable from an API key.** Checked 2026-09-12
against vendor documentation:

| Provider | Balance | Spend | Headroom |
|---|---|---|---|
| Anthropic | no endpoint | Usage & Cost API, **Admin key** (`sk-ant-admin01-…`), workspace keys rejected | `anthropic-ratelimit-*` headers on every response, ordinary key |
| OpenAI | no endpoint | Admin API, admin key | `x-ratelimit-*` headers on every response, ordinary key |
| Google | no endpoint | not exposed; documentation points at AI Studio | no headers documented |
| Ollama | n/a — local | n/a | n/a |

A credit page would therefore be blank for Google, and for the other two would
require an organisation-admin credential living on the laptop that goes to
client sites. Meanwhile the number that actually ends a lesson is on every
response already: four panes firing at once exhaust a per-minute token limit
long before an account runs dry.

## Decision

**1. The ceilings go.** `HARD_MAX_TOKENS` is removed; `max_tokens` becomes a
per-role session-profile parameter (ADR 0004) with no upper bound written in
this repository. `daily_token_budget` stops refusing and becomes a number that
is reported.

**2. A number Banco shows as a measurement is measured.** Real provider usage is
captured from the stream terminator on all four providers. Where a provider
genuinely cannot report, the figure is labelled an estimate wherever it appears —
never silently mixed with measured ones.

**3. Usage is shown per beat, per pane.** Input tokens across four panes is what
D3's ladder *is*: no documents, all documents, retrieved documents, with the
numbers beside them. A running cumulative counter teaches nothing; it is trainer
information and belongs on the console.

**4. Headroom, not credit.** The second page of the usage widget is rate-limit
remaining and reset, read from response headers. Cost reporting through Admin
APIs is out of scope; if it is ever added it is console-only, opt-in, and needs
its own decision — an org-admin credential on a machine used at client sites is
a bigger change than a page of numbers.

**5. Split by audience.** Token counts go on the harness; PROJECT.md already
lists them among the mechanisms the room is entitled to see. Headroom, limits
and anything about money stay on the stage console. No figure about the
trainer's account reaches the projected surface.

## Consequences

- Providers must surface usage from the streaming path. This is per-provider
  work with a per-provider test, and it is the second thing after ADR 0004's
  `prepare()` that makes the provider layer testable rather than trusted.
- `app/utils/token_budget.py` changes role from gate to ledger. `can_spend`,
  `is_budget_exhausted` and `LLMBudgetExceededError` retire; `record_usage` and
  the daily table stay and start receiving real figures.
- Pre-flight reports what a rehearsal actually spent, per provider, in tokens.
  Not in currency: a price table maintained in this repository would rot exactly
  the way the model ids do, and a wrong number about money in front of a client
  is worse than no number.
- The room sees one more thing. It is covered by objective 2, and it is real
  once decision 2 lands.
- Google's headroom page says the API does not expose it, and links out. An
  absent instrument that says it is absent is honest; a zero is not.
- Historical rows in `logs/tokens.db` are estimates and post-change rows are
  measurements, with nothing distinguishing them. The table is scratch, so it is
  cleared once on upgrade rather than migrated.

## Alternatives considered

**Raise the ceilings instead of removing them.** Rejected: a larger arbitrary
number still refuses at an arbitrary point, and the point is chosen by whoever
last edited a constant rather than by the person spending the money.

**Keep the budget as a warning rather than a refusal.** Partly adopted — that
is what "reported" means in decision 1. Rejected as a *modal* warning, because
anything that interrupts between a click and a demonstration is a hazard in a
room.

**Show cost in euros.** Rejected. It needs per-model prices maintained here,
which rot; and the failure mode is a confidently wrong figure about money,
displayed to the person paying for the workshop.

**Estimate tokens and label the display "approx".** Rejected. The estimate is
characters ÷ 4, which is wrong by different amounts per language and per
tokenizer, and D3's teaching point is a ratio between panes — precisely the
thing a per-pane systematic error destroys. The real counts are in the responses
already.
