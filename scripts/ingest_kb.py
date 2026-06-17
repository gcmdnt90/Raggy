"""
Script for ingesting the Knowledge Base into ChromaDB.

Usage:
    python scripts/ingest_kb.py                    # Full ingestion
    python scripts/ingest_kb.py --rebuild          # Rebuild from scratch
    python scripts/ingest_kb.py --test-query "your query"  # Test retrieval
"""

import os
import sys
from pathlib import Path

# ── Venv bootstrap ──────────────────────────────────────────────────────────
def _ensure_venv():
    _root = Path(__file__).resolve().parent.parent
    if sys.prefix != sys.base_prefix:
        return
    venv_python = _root / "venv" / (
        "Scripts" if os.name == "nt" else "bin"
    ) / ("python.exe" if os.name == "nt" else "python")
    if venv_python.exists():
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    else:
        print("⚠️  No active virtual environment and 'venv/' not found.")
        print("   Run start.bat (Windows) first.")
        sys.exit(1)

_ensure_venv()

import argparse  # noqa: E402
import hashlib   # noqa: E402

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import KB_ROOT, CHROMA_PERSIST_DIR, get_settings


def load_documents() -> list[dict]:
    """Auto-discover supported documents under knowledge_base/."""
    from app.parsers.documents import SUPPORTED_EXTENSIONS, load_document

    documents = []
    skip_dirs = {"chroma_db", "__pycache__", "prompts"}

    for path in sorted(KB_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        # Skip excluded directories
        if any(part in skip_dirs for part in path.parts):
            continue
        # Skip the KB README
        if path.name == "README.md" and path.parent == KB_ROOT:
            continue

        try:
            parsed = load_document(path)
        except Exception as e:
            print(f"  ⚠️  Error reading {path}: {e}")
            continue

        # Category = first subdirectory under KB_ROOT
        rel = path.relative_to(KB_ROOT)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"
        metadata = parsed.metadata.copy()
        metadata.update({
            "source_file": str(rel),
            "category": category,
            "language": "auto",
        })

        documents.append({
            "text": parsed.text,
            "metadata": metadata,
        })
        print(f"  ✅ {rel} ({len(parsed.text)} chars)")

    return documents


def chunk_documents(documents: list[dict], chunk_size: int = 800, chunk_overlap: int = 200) -> list[dict]:
    """Split documents into semantic chunks with overlap."""
    from app.utils.sanitize import sanitize_text

    chunks = []
    for doc in documents:
        text = sanitize_text(doc["text"])
        metadata = doc["metadata"]

        # Try to split on markdown headers first
        sections = []
        current = ""
        for line in text.split("\n"):
            if line.startswith("## ") and current:
                sections.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            sections.append(current)

        # Further split large sections
        for section in sections:
            if len(section) <= chunk_size:
                chunk_text = sanitize_text(section.strip())
                if chunk_text:
                    chunks.append({"text": chunk_text, "metadata": metadata.copy()})
            else:
                # Sliding window
                start = 0
                while start < len(section):
                    end = start + chunk_size
                    chunk_text = sanitize_text(section[start:end].strip())
                    if chunk_text:
                        chunks.append({"text": chunk_text, "metadata": metadata.copy()})
                    start += chunk_size - chunk_overlap

    return chunks


def create_embeddings_and_index(chunks: list[dict], rebuild: bool = False):
    """Generate embeddings and index in ChromaDB."""
    import chromadb

    persist_dir = str(CHROMA_PERSIST_DIR)

    if rebuild:
        # Release any cached ChromaDB client connections (SQLite locks)
        from app.rag.retriever import close_chroma_clients
        close_chroma_clients()
        import gc
        gc.collect()

    client = chromadb.PersistentClient(path=persist_dir)

    collection_name = "raggy_kb"
    if rebuild:
        try:
            client.delete_collection(collection_name)
            print("  Previous collection deleted")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Load embedding model
    settings = get_settings()
    print(f"  📐 Loading embedding model: {settings.embedding_model}")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(settings.embedding_model)

    # Prepare data
    texts = [c["text"] for c in chunks]
    ids = [hashlib.md5(t.encode()).hexdigest() for t in texts]
    metadatas = [c["metadata"] for c in chunks]

    # Generate embeddings
    print(f"  🧮 Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    # Upsert into ChromaDB
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        end = min(i + batch_size, len(texts))
        collection.upsert(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
        )

    print(f"  ✅ {collection.count()} chunks indexed in ChromaDB")
    return collection


def test_retrieval(query: str, k: int = 5):
    """Test retrieval with a query."""
    import chromadb
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    collection = client.get_collection("raggy_kb")
    model = SentenceTransformer(settings.embedding_model)

    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    print(f"\n🔍 Query: \"{query}\"")
    print(f"   Results (top-{k}):\n")
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        score = 1 - dist
        print(f"   {i+1}. [{meta['source_file']}] (score: {score:.3f})")
        print(f"      {doc[:120]}...\n")


def main(rebuild: bool = False):
    print("📚 Raggy — Knowledge Base Ingestion")
    print("=" * 50)

    print("\n── Step 1: Loading documents ──")
    documents = load_documents()
    print(f"\n   Total: {len(documents)} documents loaded")

    if not documents:
        print("\n⚠️  No documents found in knowledge_base/.")
        print("   Add .md, .txt, .pdf, .docx, or .xlsx files to knowledge_base/ and re-run.")
        return

    print("\n── Step 2: Chunking ──")
    chunks = chunk_documents(documents)
    print(f"   Total: {len(chunks)} chunks generated")

    print("\n── Step 3: Embedding and indexing ──")
    create_embeddings_and_index(chunks, rebuild=rebuild)

    print("\n✅ Ingestion complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raggy KB Ingestion")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the database from scratch")
    parser.add_argument("--test-query", type=str, help="Test retrieval with a query")
    args = parser.parse_args()

    if args.test_query:
        test_retrieval(args.test_query)
    else:
        main(rebuild=args.rebuild)
