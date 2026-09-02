# Domain documentation

Raggy is a single-context repository. Read `CONTEXT.md` before changing domain
behaviour and check `docs/adr/` for relevant architectural decisions. If those
paths do not exist, proceed using the terminology already present in code and
user documentation.

Security boundaries are part of the domain model: knowledge-base documents,
chat text, provider credentials, and local vector data are private by default.
The user application may answer questions, while configuration, installation,
and knowledge-base mutation are administrative operations.

