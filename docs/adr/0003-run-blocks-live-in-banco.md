# 3. Run blocks live in Banco, not in the deck

Date: 2026-09-09
Status: Accepted
Amends: [0001](0001-vendor-the-demo-database-from-the-deck.md)

## Context

ADR 0001 decided that the demo database stays in the deck, that Banco vendors a
pinned copy, and that the schema is extended "additively, with a
machine-readable `run` block per beat". The first two hold. The third places the
run blocks inside the vendored file, and that is the part this amends.

A run block is not prompt text. It is panes, model sources, sampling
parameters, pasted inputs and expected artefacts — the half of a beat that a
program executes rather than a human reads. Three consequences of putting it in
the deck became clear once M1 started:

1. **Every iteration is a two-repository round trip.** The schema is not yet
   stable: nobody has run a four-pane beat, so nobody knows what a pane needs.
   Editing the deck, re-vendoring, and bumping `DECK-PIN.txt` for each attempt
   makes the cheap experiments expensive.
2. **The divergence check stops being a comparison.** ADR 0001 wants CI to fail
   when the vendored copy drifts from its pin. If Banco also writes `run` keys
   into that copy, the check must compare everything *except* the keys Banco
   edits — a partial comparison, which is precisely the kind of check that
   stops noticing things.
3. **The deck carries a schema only Banco uses.** ADR 0001 already recorded
   this as a cost and mitigated it with a note in `PROMPTS.md`. The mitigation
   is a request that a future editor not delete something that looks like dead
   weight — in a repository whose own rule is that the deck must never fail to
   open.

## Decision

Run blocks live in Banco, in `demo/run-blocks.json`, keyed by beat id. They are
merged over the demo database at load time by `app/server/runs.py`.

`demo/demo-prompts.json` stays a **byte-identical** vendored copy of the deck at
the commit in `demo/DECK-PIN.txt`. Prompt text still has exactly one home, and
it is still the deck.

Two rules make the split safe rather than merely convenient:

- **A run block never contains prompt text.** If a prompt needs changing, it
  changes in the deck and arrives by an updated pin. A run block that embedded
  text would reintroduce the drift ADR 0001 exists to prevent.
- **A run block never names a provider.** A pane asks for a *role* — `primary`,
  `secondary`, `local` — and the profile chosen at first run binds roles to
  providers. A block naming `anthropic` could not run under the `offline`
  profile and could not degrade to replay, which PROJECT.md requires of every
  beat.

A beat with no run block is a legitimate state, not an omission: library and
archived beats have none. `run-blocks.json` carries an `_unblocked` map naming
each such beat and why, so "why can I not run this" is answerable from the
stage console without reading the source.

## Consequences

- The divergence check becomes a byte comparison of one file against one
  commit. It can be written in a line and cannot be fooled by a whitelist.
- Run blocks iterate at Banco's speed while the schema is unstable, which is
  the whole of M1.
- Two files must agree on beat ids. A run block for a beat id that no longer
  exists, or an active beat with no block, is now a possible inconsistency. It
  is checked in `tests/test_run_blocks.py` rather than left to discovery in a
  room.
- The deck no longer carries a schema it does not use, and the note in
  `PROMPTS.md` asking editors to preserve one can go.
- If the run blocks ever stabilise and a second consumer needs them, this
  decision is cheap to reverse: the merge point is one module.

## Alternatives considered

**Author in the deck, as ADR 0001 says.** One source of truth for a whole beat,
and no possibility of the two files disagreeing about beat ids. Rejected for
now on iteration cost alone — the deck is the artefact that must never fail to
open, and it should not absorb churn from a schema that is still being
discovered. Worth revisiting once the schema has survived a delivery.

**Edit the vendored copy and teach the check to ignore `run` keys.** Least
friction today. Rejected: it converts the divergence check from a byte
comparison into a partial one, and a check with an ignore list silently stops
watching whatever is on that list.

**Put run blocks in Python.** Rejected by AGENTS.md rule 5 in spirit and by
practice: the parameters are data a trainer may want to change between two
deliveries, and they should not require an edit to a module to change.
