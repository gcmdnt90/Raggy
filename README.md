# Banco

**The demonstration harness for Workshop 1 of the AI Translator lesson.**

Banco runs the five demonstrations with the mechanism visible: which model
answered, at what temperature, with what system prompt, over which retrieved
passages, and where the request went.

It is a fork of [Raggy](https://github.com/gcmdnt90/Raggy), which remains a
separate tool.

## Quick start

```bat
start.bat
```

Creates a virtual environment, installs dependencies, runs the setup wizard on
first launch, and opens **pre-flight** — the stage console — at

    http://127.0.0.1:8501/console

Banco opens there on every launch, not only when it looks unconfigured: the
machine that fails is the one that worked last week. `admin.bat` just opens the
same URL.

The projected surface is a different route, and it is the only one safe to put
on a projector — `/` redirects to the console and the console shows key fields:

    http://127.0.0.1:8501/harness

## First run asks for two things

**A profile.** At least one model source is required; two are recommended. A
source is an API provider (Anthropic, OpenAI, Google) or a local Ollama model.

| Profile | Sources | Behaviour |
|---|---|---|
| `classroom` | 2–3 API keys + Ollama | everything live |
| `take-home` | 1 API key (± Ollama) | live except beats needing a second source |
| `offline` | Ollama only | D4 and D5-B replay; the rest live |

A missing source degrades a beat to a replayed recording. It never removes it.

**A sector** — one of the six the demo database declares (`numismatics`,
`photovoltaic`, `automation-software`, `defi-protocol`, `trade-association`,
`knitwear-software`) — which drives every prompt and every folder. Pre-flight
says which of them has its material generated on this machine, and prints the
`demo/kit/generate.py` command for one that does not.

## The demonstrations

| | Shape | What it teaches |
|---|---|---|
| D1 | varianza | sampling variance; fields absent from the source get filled anyway |
| D2 | giudizio | capability differs by model; deliberation is a budget, not a switch |
| D3 | scala | no documents → all documents → retrieved documents |
| D4 | costruzione | standing instructions condition but do not block; an agent chooses what to read |
| D5 | attacco | the data path · injection · confident wrong attribution |

## Documentation

- `PROJECT.md` — objectives, non-goals, milestones, decisions
- `AGENTS.md` — for AI agents developing, installing or repairing Banco
- `CONTEXT.md` — vocabulary local to this codebase
- `docs/adr/` — implementation decisions

Framework decisions live in the AI Translator repository under `docs/adr/`.

## Status

**M0 done** — both locks regenerated on Windows with Python 3.13, Streamlit and
qdrant-client gone (`AGENTS.md` §3).

**M1–M2 in progress.** Four of the thirty-two declared beats execute live today:
`m1-p1`, `m1-p2`, `m2-p1`, `m2-p2`. Every other beat carries a recorded reason
for why it cannot, shown beside it rather than left to be discovered in a room.
`run-blocks.json` is the register of both.

**M3 (record and replay) has not started**: a pane that cannot run says so and
shows nothing, because there is no recording to show.

## License

Apache 2.0, inherited from Raggy.
