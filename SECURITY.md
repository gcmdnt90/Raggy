# Security policy

Please report vulnerabilities privately to the repository owner. Do not open a
public issue containing credentials, private knowledge-base content, chat logs,
or a working exploit against an exposed instance.

Supported development occurs on the latest `master` branch. Security fixes are
not backported to older snapshots.

## Deployment baseline

- Run both Streamlit applications on loopback unless a trusted reverse proxy
  supplies authentication and TLS.
- Never expose an embedded vector store as a network service.
- Keep `.env`, `logs/`, and `knowledge_base/` access limited to the local user.
- Apply dependency updates through `update.bat` and retain them only after the
  automated tests and dependency audit pass.

