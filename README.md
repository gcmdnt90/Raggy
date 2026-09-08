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
first launch, and opens the harness at `http://127.0.0.1:8501`.

The stage console — pre-flight, configuration, prompt inspection, logs — is a
route on the same server, authenticated and never projected:

    http://127.0.0.1:8501/console

`admin.bat` just opens it.

## First run asks for two things

**A profile.** At least one model source is required; two are recommended. A
source is an API provider (Anthropic, OpenAI, Google) or a local Ollama model.

| Profile | Sources | Behaviour |
|---|---|---|
| `classroom` | 2–3 API keys + Ollama | everything live |
| `take-home` | 1 API key (± Ollama) | live except beats needing a second source |
| `offline` | Ollama only | D4 and D5-B replay; the rest live |

A missing source degrades a beat to a replayed recording. It never removes it.

**A sector** — `numismatics`, `photovoltaic` or `automation-software` — which
drives every prompt and every folder.

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

Pre-M0. The fork is in place and both clean-checkout defects inherited from
Raggy are fixed, but `requirements.lock` has not yet been regenerated — see
`AGENTS.md` §3.

## License

Apache 2.0, inherited from Raggy.
