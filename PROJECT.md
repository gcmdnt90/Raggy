# Banco

**Banco is the demonstration harness for Workshop 1 of the AI Translator
lesson.** It runs the five demonstrations (D1–D5) with the mechanism exposed:
provider and model per pane, sampling temperature, thinking budget, token
counts, the system prompt as sent, retrieved passages, every tool call, and the
destination of every network request.

It is a fork of [Raggy](https://github.com/gcmdnt90/Raggy), which continues to
exist as a separate tool with a different job. See
[ADR 2](#decisions-and-where-they-are-recorded).

---

## Why it exists

The 2026-09-02 delivery ran out of time and most demonstrations were described
rather than performed. Five demos ran on five vendor products, each with its own
login, setup and failure surface — and the products hide precisely what the
lesson is about. No consumer chat interface exposes temperature, which is why
the temperature beat (`m1-p3`) has been a dead branch since it was written. A
Claude Project silently switches from context-stuffing to retrieval as the
knowledge base grows, so the middle rung of the D3 ladder cannot be shown doing
either.

Banco replaces the five surfaces with one, and makes the hidden things visible.

---

## Objectives

Each is written so that it can be checked, not admired.

1. **One setup.** A trainer completes pre-flight for all five demonstrations in a
   single application, on a single machine, in one pass.
2. **Every mechanism visible.** For any beat, the room can see which model
   answered, at what temperature, with what system prompt, over which retrieved
   passages, and where the request went.
3. **No beat is ever merely described.** Every demonstration can run live, and
   every demonstration can be replayed from a recording of a real run when live
   fails. See ADR 3.
4. **Three currently unshowable beats become live:** `m1-p3` (temperature),
   `m3-p3` (lost in the middle), and the D3 rung-2 mechanism itself.
5. **The D3 ladder is named by mechanism, not by brand:** no documents → all
   documents → retrieved documents.
6. **An agent can install it.** A capable AI agent, given only this repository,
   can complete installation unattended up to the point where a human must paste
   an API key, and can guide a non-technical person through the rest. See
   `AGENTS.md`.
7. **Nothing on the projected surface leaks.** No API key, no client name, no
   ground-truth file, no trainer note ever renders in the demo application.

## Non-goals

- **Banco is not a product participants adopt.** It is a delivery vehicle. What
  they adopt is whatever their organisation already owns; the closing tool
  segment is where they meet it.
- **Banco is not a replacement for Raggy.** Raggy remains the Workshop 2
  construction scaffold in the framework glossary.
- **Banco is not a multi-stack project.** Python and one dependency-free browser
  page. No UI framework, no build step, no second server or port. The
  implementation is written by AI agents from this document and `AGENTS.md`, and
  every extra choice offered is a wrong turn available to take.

- **Banco is not a general agent framework.** The agent loop exists to be *shown*
  and must stay small enough to put on a projector. Do not vendor Hermes,
  OpenClaw or similar; borrow ideas, not code.
- **Take-home is best-effort.** Banco must work in the lesson and may work at
  home. A thin laptop cannot run a useful local model, so the take-home path is
  an API key, not Ollama.
- **The deck rework is out of scope for now.** Demo slides change only once
  Banco works.

- **Banco does not rely on surprise.** The complete demonstration material ships,
  answer key included. Nothing in the lesson depends on a participant not having
  read it — a demonstration whose value evaporates once the audience knows the
  answer is a trick, not a demonstration. See AI Translator `docs/adr/0004`.
  One practical consequence: D4 beat 8 is run as a verification the room performs
  together, not as a reveal the trainer performs at them.

---

## What each demonstration needs

| Demo | Shape | Mechanism taught | Needs an agent loop? | Local-only capable? |
|---|---|---|---|---|
| D1 | varianza | sampling variance; fields absent from the source get filled anyway | no | partly — sampling yes, cross-source disagreement needs a second source |
| D2 | giudizio | capability differs by model; deliberation is a budget, not a switch | no | yes — `qwen3:1.7b` vs `qwen3:8b`, `think` toggle and levels |
| D3 | scala | no documents → all documents → retrieved documents | no | yes |
| D4 | costruzione | standing instructions condition but do not block; an agent chooses what to read | **beats 7–8 yes** | no |
| D5 | attacco | A: the data path. B: injection. C: confident wrong attribution | **B yes** | A by definition; C yes |

Prompt text is never written here. It lives in the demo database
(`demo/demo-prompts.json`).

---

## Configuration model

**Model sources.** At least one (local or API); two recommended (local + API, or
two APIs). A missing source **degrades a beat to replay — it never removes it**.

**Profiles**, chosen once at first run:

| Profile | Sources | Behaviour |
|---|---|---|
| `classroom` | 2–3 API keys + Ollama | everything live |
| `take-home` | 1 API key (± Ollama) | live except the beats that need a second source |
| `offline` | Ollama only | D4 and D5-B replay; the rest live |

**Sector** is chosen once and drives every prompt, widget and folder, exactly as
it does in the deck. The database declares six — `numismatics`, `photovoltaic`,
`automation-software`, `defi-protocol`, `trade-association`,
`knitwear-software` — and `demo/kit/` can generate a pack for each. The ids are
English; each sector's `data.folder` in the database names the Italian folder
under `demo/data/` (`numismatica`, `fotovoltaico`, `automazione`, `defi`,
`associazione`, `maglieria`) and `data.records_dir` the records folder D4 works
over. Never hard-code either mapping, and never restate the list as though it
were closed: adding a sector is a config plus a generator module, and pre-flight
reads the set from the database.

---

## Invariants

1. **Projected surface.** The demo application must never render an API key or a
   client name — those are confidential — nor `_perito/ground-truth.csv`,
   `LEGGIMI-CATENA.md` or any trainer note, which are not confidential but are
   trainer material and belong to the stage console or the deck's speaker view.
   The rule is about focus and about credentials, not about secrecy: see
   *Banco does not rely on surprise* below.
2. **Replay, never simulation.** Banco may replay a recording of a real run,
   announced as such. Banco must never display output that no model produced.
   See ADR 3.
3. **The chain never waits.** Every handover file `d1-bozze.md` … `d5-verifiche-umane.md`
   exists on disk before the lesson. A successful run overwrites it; a failed one
   is narrated and the file is opened.
4. **The data path is always visible.** Every call shows its destination. Without
   this, D5-A's network-off gesture proves nothing, because the room never saw
   anything leave in the first place.
5. **Never invent facts about the client's business.** Inherited verbatim from
   `theory-deck/PROMPTS.md`; it applies to Banco's fixtures and recordings too.

---

## Milestones

**M0 — fork hygiene.** Clean-checkout CI (`git clone` → fresh venv → import →
tests). Regenerate `requirements.lock` from the corrected `pyproject.toml`.
Confirm the inherited Raggy applications still run.

**M1 — the spine.** Demo database schema extended with machine-readable `run`
blocks; demo selector D1–D5; multi-pane execution over Server-Sent Events; the
egress indicator; provider and profile configuration on the console. The FastAPI
skeleton and both surfaces exist in outline already — see `docs/adr/0002`.

**M2 — the demonstrations that need no agent.** D1, D2, D3 (all three rungs),
D5-A, D5-C. At the end of M2 a lesson is deliverable with D4 and D5-B still run
in Cowork as a temporary bridge.

**M3 — record and replay.** Capture during the dry run; replay with a visible
indicator; recordings versioned beside the demo data.

**M4 — the stage console.** The admin application becomes pre-flight: providers
reachable, models pulled, sector chosen, chain files present, recordings fresh.

**M5 — the agent loop.** `list_dir` / `read_file` / `write_file` over one
sandboxed folder, tool calls streamed on screen, a permission prompt that is
itself teaching material. D4 beats 7–8 and D5-B come home.

**M6 — take-home packaging.** Deferred until the above works.

---

## Decisions and where they are recorded

Framework-level decisions — what the lesson does — live in the AI Translator
repository. Implementation decisions live in `docs/adr/` here.

| Decision | Where |
|---|---|
| Demonstrate mechanisms in a purpose-built harness, not on vendor products | AI Translator `docs/adr/0001` |
| Banco is a separate repository, forked from Raggy | AI Translator `docs/adr/0002` |
| Replay, never simulation | AI Translator `docs/adr/0003` |
| The demo database stays in the deck; Banco vendors a pinned copy | `docs/adr/0001` (here) |
| One FastAPI server, two surfaces; Streamlit removed | `docs/adr/0002` (here) |

Shared vocabulary — **Banco**, **Replay**, **Data path**, **Tool category vs.
delivery vehicle** — is defined in the AI Translator `CONTEXT.md`. Terms local to
this codebase are in `CONTEXT.md` here.

---

## Open questions

- Which model tier the agent loop needs before D4 lands as well as it does in
  Cowork today. Assume a cloud provider; measure at M5.
- Whether the deck keeps per-demo slides or collapses to one DEMO slide.
  Deferred until Banco works.
- Whether a participant-facing take-home brief exists at all, and under what
  name. Deferred with the deck rework.
