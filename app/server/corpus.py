"""The sector's own documents, and the three ways D3 puts them into a context.

D3 is the ladder: **no documents → all documents → retrieved documents**. The
same question on all three rungs, so the only thing that differs between the
panes is what is in the context — which is the whole mechanism the beat exists
to show, and the middle rung is the one no vendor product can be made to
expose, which is why D3 is in Banco at all (PROJECT.md, *Why it exists*).

Three rules hold this module together.

**Rooted per sector**, exactly like `runs.read_input_file` and for the same
reason: one sector's beat must not be able to read another's material. It is
also why the Chroma collection is named per sector instead of reusing Raggy's
single `raggy_kb` — one shared collection would make rung 3 answer out of
whichever sector happened to be indexed last, and it would do it *plausibly*,
which is the worst way for it to be wrong.

**The index is built on the console, never in the room.** The first build loads
a sentence-transformers model and may download it. `index_state` answers whether
that has already happened *without loading anything*, so pre-flight can report
it in milliseconds and a lesson never discovers a 470 MB download at the
projector. `scripts/build_index.py` is the build.

**One document, one copy.** `demo/data/<sector>/regole/` ships the same content
twice, as `.md` and as `.pdf`, because the room downloads the PDF. Indexing both
would retrieve the same passage twice under two names and make rung 3 look like
it found corroboration where there is one source. Markdown wins; a PDF is
indexed only when it has no markdown sibling.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.i18n import t
from app.server.demos import data_root

logger = logging.getLogger("raggy.corpus")

#: Where a sector keeps the documents D3 climbs. A run block may override it
#: with `corpus.dir`; this is the default because every generated pack has one.
DEFAULT_CORPUS_DIR = "regole"

#: Chunking. Deliberately large and paragraph-aligned: these passages are
#: projected, and a room reading a 200-character fragment learns that retrieval
#: returns confetti. A whole clause of a house rule is the unit that makes the
#: rung legible.
CHUNK_CHARS = 900
CHUNK_OVERLAP = 120

#: How many passages rung 3 retrieves. Four fits on a projected pane and is
#: enough for the beat's point — that the answer is grounded in *these*, and
#: that the room can check them.
DEFAULT_TOP_K = 4

TEXT_SUFFIXES = {".md", ".txt"}
PDF_SUFFIXES = {".pdf"}


@dataclass(frozen=True, slots=True)
class Passage:
    """One retrievable piece of the sector's material.

    `source` is the path relative to the sector root, so it is safe to project
    and means something to a room looking at the same folder on screen.
    """

    source: str
    text: str
    score: float = 0.0

    def as_dict(self) -> dict:
        return {"source": self.source, "text": self.text, "score": round(self.score, 3)}


def corpus_root(sector: str, folder: str | None = None) -> Path:
    """The folder this sector's documents live in, refusing to escape it."""
    root = data_root(sector).resolve()
    target = (root / (folder or DEFAULT_CORPUS_DIR)).resolve()
    if not target.is_relative_to(root):
        raise ValueError(t("corpus.escapes_sector", path=repr(folder)))
    return target


def documents(sector: str, folder: str | None = None) -> list[tuple[str, str]]:
    """Every document in the sector's corpus as (relative path, text).

    Sorted, so that two builds of the same folder produce the same index and a
    rehearsal and a lesson retrieve the same passages in the same order.
    """
    root = corpus_root(sector, folder)
    if not root.is_dir():
        return []

    sector_root = data_root(sector).resolve()
    found: list[tuple[str, str]] = []
    stems_with_text = {
        path.stem for path in root.rglob("*") if path.suffix.lower() in TEXT_SUFFIXES
    }

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        relative = path.relative_to(sector_root).as_posix()
        if suffix in TEXT_SUFFIXES:
            found.append((relative, path.read_text(encoding="utf-8")))
        elif suffix in PDF_SUFFIXES and path.stem not in stems_with_text:
            # Only when there is no markdown twin. See the module docstring.
            try:
                from app.parsers.documents import parse_document

                found.append((relative, parse_document(path)))
            except Exception:  # noqa: BLE001 - a corpus is not worth a 500
                logger.warning("Could not read %s; left out of the corpus", relative)
    return found


def all_documents_text(sector: str, folder: str | None = None) -> str:
    """Rung 2: every document, whole, one after another.

    Each is headed with its own path. Without that the model receives one
    undifferentiated wall and the room cannot tell that this rung had the
    documents at all — and telling them apart is half of what rung 2 teaches.
    """
    parts = [f"--- {source} ---\n{text.strip()}" for source, text in documents(sector, folder)]
    return "\n\n".join(parts)


def chunks(sector: str, folder: str | None = None) -> list[Passage]:
    """The corpus split into retrievable passages, paragraph-aligned."""
    out: list[Passage] = []
    for source, text in documents(sector, folder):
        for piece in _split(text):
            out.append(Passage(source=source, text=piece))
    return out


def _split(text: str) -> list[str]:
    """Paragraphs, glued up to CHUNK_CHARS, with a little overlap.

    Splitting on blank lines rather than on a character count keeps a rule and
    its heading together, which is what makes a retrieved passage readable when
    it is the thing on the projector.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= CHUNK_CHARS or not current:
            current = candidate
            continue
        pieces.append(current)
        tail = current[-CHUNK_OVERLAP:] if CHUNK_OVERLAP else ""
        current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
    if current:
        pieces.append(current)
    return pieces


# ── the index ───────────────────────────────────────────────────────────────

def collection_name(sector: str) -> str:
    """One collection per sector. Never Raggy's `raggy_kb`."""
    return "banco_" + re.sub(r"[^a-z0-9_-]+", "-", sector.lower())


def _client():
    from app.config import CHROMA_PERSIST_DIR
    from app.rag.retriever import get_chroma_client

    return get_chroma_client(str(CHROMA_PERSIST_DIR))


def index_state(sector: str) -> dict:
    """Whether this sector's index exists, and how big — loading no model.

    Pre-flight calls this on every page load, so it must not be the thing that
    pulls 470 MB of sentence-transformers down a conference-centre connection.
    Chroma is asked for a count; nothing is embedded.
    """
    name = collection_name(sector)
    try:
        collection = _client().get_collection(name)
        return {"collection": name, "ready": True, "chunks": collection.count()}
    except Exception:  # noqa: BLE001 - "not built" is the common, expected case
        return {"collection": name, "ready": False, "chunks": 0}


def _embedder():
    from app.config import get_settings
    from app.rag.embeddings import EmbeddingManager

    return EmbeddingManager(hf_token=get_settings().hf_token)


def build_index(sector: str, folder: str | None = None) -> dict:
    """Build or rebuild this sector's index. Slow, deliberate, off the harness.

    Dropping and recreating rather than upserting: the corpus is small, and a
    collection that accumulates across builds would quietly serve passages from
    a document the trainer has since deleted.
    """
    pieces = chunks(sector, folder)
    if not pieces:
        raise FileNotFoundError(t("corpus.empty", sector=sector))

    name = collection_name(sector)
    client = _client()
    try:
        client.delete_collection(name)
    except Exception:  # noqa: BLE001, S110 - nothing to delete on a first build
        logger.debug("No existing collection %s to drop", name, exc_info=True)

    collection = client.create_collection(name)
    vectors = _embedder().embed([p.text for p in pieces])
    collection.add(
        ids=[f"{sector}-{i}" for i in range(len(pieces))],
        documents=[p.text for p in pieces],
        embeddings=vectors,
        metadatas=[{"source": p.source} for p in pieces],
    )
    logger.info("Indexed %s passages for %s", len(pieces), sector)
    return {"collection": name, "ready": True, "chunks": len(pieces),
            "documents": sorted({p.source for p in pieces})}


def retrieve(sector: str, query: str, k: int = DEFAULT_TOP_K) -> list[Passage]:
    """Rung 3: the passages this question actually pulled back.

    Raises `LookupError` when the index is not built. That is deliberate and it
    is not a crash: `runs.bind_panes` turns it into an unavailable pane with the
    reason on it, so the ladder still shows rungs 1 and 2 and the room is told
    which rung did not run. Inventing passages, or silently falling back to
    rung 2, would be the harness lying about its own mechanism — invariant 2.
    """
    state = index_state(sector)
    if not state["ready"] or not state["chunks"]:
        raise LookupError(t("corpus.index_missing", sector=sector))

    collection = _client().get_collection(state["collection"])
    embedding = _embedder().embed([query])[0]
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(k, state["chunks"]),
        include=["documents", "metadatas", "distances"],
    )
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]
    return [
        Passage(source=(meta or {}).get("source", "?"), text=doc, score=max(0.0, 1 - dist))
        for doc, meta, dist in zip(docs, metas, distances, strict=False)
    ]


def context_block(passages: list[Passage], lang: str | None = None) -> str:
    """The retrieved passages as they are handed to the model.

    Headed and attributed, because objective 2 puts this on the projector: the
    room has to be able to read the passage, see which file it came from, and
    then check whether the answer actually used it.
    """
    if not passages:
        return ""
    body = "\n\n".join(f"[{p.source}]\n{p.text.strip()}" for p in passages)
    return f"{t('corpus.context_heading', lang)}\n\n{body}"
