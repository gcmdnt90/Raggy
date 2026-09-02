# Raggy context

Raggy is a self-hosted Retrieval-Augmented Generation assistant. It parses a
local knowledge base, creates local vector embeddings, retrieves relevant
chunks, and sends a guarded prompt to one configured LLM provider.

## Terms

- **User app**: the chat-facing Streamlit application. It must not expose
  credentials or administrative machine controls.
- **Admin app**: the authenticated, loopback-only Streamlit application for
  configuration, prompt editing, indexing, and operational logs.
- **Knowledge base (KB)**: private source documents under `knowledge_base/`.
- **Vector store**: an embedded, on-disk index derived from the KB. It is
  rebuildable and must not expose a network service.
- **Provider credential**: an API key or token stored only in `.env` and never
  returned to a browser or written to logs.
- **Reindex**: rebuild the vector store from the current KB documents.

## Security invariants

- Default network binding is loopback.
- Administrative operations require authentication.
- Secrets are accepted as write-only values and are redacted from logs.
- Uploaded archives are bounded by compressed and decompressed size.
- Dependency resolution is locked and tested before updates are accepted.

