# Raggy Operator Runbook

## Before the Demo

- Set provider spend alerts before opening Raggy.
- Configure `DAILY_TOKEN_BUDGET` in `.env`.
- Prepare and index the knowledge base, then close the admin panel.
- Set OS auto-lock to 1 minute or less.
- Clear browser state if the machine is shared.

## During the Demo

- Start only the user app unless admin work is required.
- Do not leave the admin panel running unattended.
- Keep the provider spend dashboard visible on a second monitor when using a cloud LLM.
- Stop the demo if the budget banner turns red.

## Quick Checks

- Admin panel binds to `127.0.0.1:8502`.
- The sidebar shows `Reset conversation`.
- Oversized or invalid PDFs are rejected with a readable error.
- `.md`, `.txt`, `.pdf`, `.docx`, and `.xlsx` documents can be indexed.
