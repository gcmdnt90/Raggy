# 2. One FastAPI server, two surfaces; Streamlit removed

Date: 2026-09-05
Status: Accepted

## Context

Banco inherited Streamlit from Raggy. The inherited UI code splits unevenly:
roughly 205 lines were the chat surface and roughly 811 lines were settings and
admin panels.

The chat surface becomes the **harness** — the thing a room of a client's staff
looks at. It has to do four things Streamlit is poor at:

- **Stream several panes at once.** D1 shows four drafts simultaneously.
  Streamlit re-runs the script on every interaction and does not let background
  threads write to the UI without `add_script_run_ctx`. Possible; fiddly. Fiddly
  live is the problem Banco exists to remove.
- **Pace a reveal.** Show a thinking block, wait, then the answer, on the
  trainer's beat. Streamlit has no notion of "advance".
- **Control typography and hold a persistent header.** Legibility from the back
  of a room, plus the always-visible egress indicator, via CSS rather than
  injection hacks.
- **Stream tool calls as they happen** (M5).

A second consideration decided the scope. Banco's implementation is written by
AI agents from `PROJECT.md` and `AGENTS.md`. A repository containing two UI
frameworks, two servers and two ports is a specification that invites an agent
to choose wrongly.

## Decision

One FastAPI application on `127.0.0.1:8501`, serving two surfaces as routes:

    /          the harness       — projected
    /console   the stage console — authenticated, never projected

Streamlit is removed entirely: `app/gui/`, `app/main.py`, `app/admin.py` and
`.streamlit/` are deleted, and `app/i18n.py` no longer depends on
`st.session_state`. `start.bat` launches the server; `admin.bat` opens the
console route rather than starting a second application.

Streaming is Server-Sent Events. The browser page is plain HTML, CSS and
JavaScript with no build step and no framework — the same shape as the
theory-deck's `widgets/theory-widgets.js`.

## Consequences

- The harness gets exact control of layout, type size and reveal pacing, which
  are the properties that make it legible in a room.
- **The sidecar option stays open.** Because the harness speaks HTTP, the deck
  itself can later become the surface: reveal.js on the projector calling
  `localhost`, the demo rendering on the slide that already carries the prompt
  and the sector selector. That removes the last context switch. This decision
  does not commit to it and does not require it.
- One command, one port, one paradigm — which is what both the install contract
  and the agent-written implementation need.
- The console's 811 lines of Streamlit forms are gone and must be rebuilt. Much
  of what they did is Raggy-specific (knowledge-base management, prompt editing)
  and Banco does not need it in the same form: the console is pre-flight checks,
  provider configuration and sector selection.
- `fastapi` and `uvicorn` are declared with lower bounds only. **M0 must pin
  them** when the locks are regenerated.
- Python remains the only language in the codebase. The browser page is markup
  and script, not a second stack to maintain.

## Alternatives considered

**Keep Streamlit for both.** Cheapest and defensible — there is no deadline. It
was rejected because the discovery that it does not work happens during M2, on
top of the demos, which is the expensive moment to discover it.

**FastAPI for the harness, Streamlit for the console.** The original proposal.
Rejected once the implementation was understood to be agent-written: two
frameworks in one repository is a worse specification than either alone.

**Streamlit now, extract later.** The extraction lands exactly when the demos
work and nobody wants to touch them.
