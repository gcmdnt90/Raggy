# Knowledge Base

This directory contains the documents used by Raggy's RAG pipeline.

## How to populate

1. **Create subdirectories** for each category/topic:
   ```
   knowledge_base/
   ├── guides/
   │   ├── getting_started.md
   │   └── best_practices.md
   ├── regulations/
   │   └── compliance.md
   ├── faq/
   │   └── common_questions.md
   └── README.md   ← you are here
   ```

2. **Add documents** (`.md`, `.txt`, or `.pdf` files) to the appropriate directories.

3. **Index the KB** by running:
   ```bash
   python scripts/ingest_kb.py --rebuild
   ```
   Or from the Admin Panel → Knowledge Base → "Re-index entire KB"

## File formats

- **Markdown** (.md) — recommended for structured content
- **Plain text** (.txt) — simple unformatted text
- **PDF** (.pdf) — automatically extracted via pdfplumber

## Tips

- Split large documents into focused topics for better retrieval accuracy
- Use Markdown headings (`## Section`) — the chunker splits on them
- Each subdirectory becomes a "category" in the search metadata
- Re-index after adding, editing, or removing documents
