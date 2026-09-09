# Security policy

Please report vulnerabilities privately to the repository owner. Do not open a
public issue containing credentials, private knowledge-base content, chat logs,
or a working exploit against an exposed instance.

Supported development occurs on the latest `master` branch. Security fixes are
not backported to older snapshots.

## Deployment baseline

- Run the server on loopback unless a trusted reverse proxy supplies
  authentication and TLS. Both surfaces are routes on it; the stage console
  at `/console` additionally requires authentication.
- Never expose an embedded vector store as a network service.
- Keep `.env`, `logs/`, and `knowledge_base/` access limited to the local user.
- Apply dependency updates by regenerating the locks and re-running the
  clean-checkout verification in `AGENTS.md` §3; retain them only after the
  automated tests and the dependency audit pass.


## Banco's second threat model

Raggy's baseline above assumes a single self-hosted user. Banco is additionally
**distributed to workshop participants** and, from milestone M5, **runs an agent
that writes files on their machines**. That adds obligations Raggy does not have.

- **Participant-supplied credentials.** Keys are pasted by non-technical people
  who may be sharing a screen. They are write-only in the interface, stored only
  in `.env`, redacted from logs, and never rendered by the harness.
- **The harness is a projected surface.** Anything it renders is visible to a
  room of a client's staff. No credential, client name, ground-truth file or
  trainer note may appear there. Trainer-facing material belongs to the stage
  console, which is loopback-only and authenticated.
- **Agent file access is sandboxed to one folder**, chosen explicitly, with the
  permission prompt shown on screen — it is teaching material, not friction to
  be optimised away. No write outside the chosen folder, ever.
- **Demonstration data is deliberately hostile.** `demo/data/<sector>/avvelenata/`
  contains prompt-injection payloads by design. It must never be indexed, read or
  executed outside the demonstration that calls for it.
- **Clean-checkout validation is a security control here**, not just hygiene: an
  undeclared dependency silently pulled from a developer's machine is a supply
  chain the participant never agreed to.
