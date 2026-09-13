# Session profiles

One file per saved configuration. A profile says which **provider**, **model**
and **parameters** each role (`primary`, `secondary`, `local`) gets, with
optional per-demo overrides. It is chosen at pre-flight, never mid-lesson.

Activate one by setting `SESSION_PROFILE=<name>` in `.env` — the console writes
that scalar, and the name is the file's stem. No profile, a missing file or an
unreadable one all fall back to the derived binding Banco used before profiles
existed, so an install that has never seen one keeps working.

See [ADR 0004](../../docs/adr/0004-session-profiles-bind-roles-to-sources.md)
for why the binding moved here and
[the spec](../../docs/specs/model-control.md) for the schema.

## Three rules

**No credentials, ever.** These files are committed, read aloud and shown on a
console screen. `provider_kwargs` stays the only path a key takes into the
process. A profile carrying an `api_key`, a `token`, a `password` or a
`base_url` is refused whole rather than quietly stripped.

**A run block wins where it speaks.** Precedence is

    run-block pane  >  demos.<demo_id>  >  defaults  >  provider default

A parameter written on a pane in `run-blocks.json` is didactics — it is what
the beat exists to show — and no profile may contradict it. `m1-p1` states
`temperature: 1.0` on all four panes, so no profile can lower it;
`tests/test_precedence.py` runs against every file in this folder and fails if
one tries.

**A dropped role stays dropped.** A role whose provider has no key, or whose
Ollama is not answering, is simply absent. It does not slide onto another
provider. The pane is then marked unavailable and the beat degrades to replay,
which is what PROJECT.md requires — substituting silently would show the room
four working panes and teach the wrong lesson about what their own setup can do.

## Schema

```json
{
  "version": 1,
  "name": "classroom-due-api",
  "updated": "2026-09-12",
  "note": "read aloud at pre-flight; no secrets",

  "defaults": {
    "primary":   {"provider": "anthropic", "model": "...", "params": {"max_tokens": 16000}},
    "secondary": {"provider": "google",    "model": "...", "params": {"max_tokens": 8000}},
    "local":     {"provider": "ollama",    "model": "qwen3:8b"}
  },

  "demos": {
    "m2": {
      "primary":   {"provider": "ollama", "model": "qwen3:8b",   "params": {"think": "high"}},
      "secondary": {"provider": "ollama", "model": "qwen3:1.7b", "params": {"think": false}}
    }
  }
}
```

`demos` is keyed by demo id (`m1`…`m5`) and **merges per role**: an entry that
rebinds `primary` leaves `secondary` and `local` on the defaults. Per-file
merging would make a one-line override silently unbind the other two, which in
a lesson reads as two panes that stopped working.

`params` is Banco's own vocabulary and nothing else crosses into a provider:

| name | meaning | shape |
|---|---|---|
| `temperature` | sampling temperature | 0.0–1.0 |
| `max_tokens` | ceiling on this turn's generation | int, unbounded |
| `system` | system prompt, sent as a system message or instruction | string |
| `think` | deliberation budget | `false`, `"low"`/`"medium"`/`"high"`/`"max"`, or a token budget |

`think` is one field with three shapes because the vendors do not agree, and
because D2's mechanism is that deliberation is a *budget* and not a switch. The
adapter translates it; where it cannot, the parameter is **dropped with a
reason that reaches the screen** rather than approximated. Of the four sources
only Anthropic and Ollama express deliberation as something other than a level —
Anthropic as a token budget, Ollama as booleans *or* levels — so the pane that
carries D2's claim should be one of those two.

## Model ids

Never hand-written from memory. A profile is written by the console from what
live discovery returned, so the file records a choice a human made from a real
list. A model that has since been retired fails at pre-flight with the
provider's own 404 and the current list beside it, labelled with whether that
list came from the API or from the static backstop.

Leaving `model` out is legal and means "whatever this provider class declares",
which is what the example below does for the API roles: those ids rot fastest.
