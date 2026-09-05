# 1. Vendor the demo database from the deck, pinned

Date: 2026-09-05
Status: Accepted

## Context

Prompt text for every demonstration lives in `demo-prompts.json`, in the
`theory-deck` repository (`gcmdnt90/AI-theory-deck`). Eight files there already
read it: `build.mjs`, `template.html`, `widgets/theory-widgets.js`, four module
HTML files and `academic.html`. `theory-deck/PROMPTS.md` states the reason —
one source of truth, so the prompt on the slide, in the run-sheet and in the
trainer's hand cannot drift.

Banco becomes a third consumer, in a different repository. A fourth is likely
later if a participant-facing take-home brief is written.

Two constraints are non-negotiable. The deck must open from `file://` in a room
with no internet, so it cannot fetch anything at runtime. And Banco must run in
the same room, under the same conditions.

## Decision

The demo database stays in the deck. Banco **vendors a copy** at
`demo/demo-prompts.json`, with the source commit recorded in
`demo/DECK-PIN.txt` (currently `f035474`). Nothing is fetched at runtime.

The schema is extended, additively, with a machine-readable `run` block per
beat: panes, provider and model per pane, temperature, thinking level, input
files, expected artefact. Today `prompt.tool` is free text — `"Cowork — project
instructions"`, `"Raggy — rung 3, paste the criteria of D2"` — which a human
reads and a program cannot execute. The deck ignores `run`; nothing there
breaks.

Banco's CI compares its vendored copy against the pinned deck commit and fails
on divergence, so a copy cannot rot silently.

## Consequences

- Offline works in both consumers, which is the hard requirement.
- Prompt edits happen in one place and reach Banco by an explicit, reviewable
  update of the pin.
- The pin is a manual step and will occasionally be forgotten. The CI check turns
  that from a silent drift into a failing build.
- The deck repository now carries a schema that only Banco uses. Documented in
  `PROMPTS.md` so a deck editor does not delete it as dead weight.

## Alternatives considered

**Promote the database to its own repository or package.** Cleaner ownership
with four consumers, at the cost of a third repository to release. Revisit when
a fifth consumer appears.

**Banco owns it, the deck vendors a copy.** Defensible now that Banco is the
primary runner, but it makes the deck depend on the application rather than the
reverse, and the deck is the artefact that must never fail to open.

**Fetch at runtime.** Rejected outright: both consumers must work with no
network.
