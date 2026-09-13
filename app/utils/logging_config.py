"""
Logging configuration for Raggy.

Call setup_logging() once at app startup. Writes DEBUG+ to rotating daily log
files in logs/, WARNING+ to console. Suppresses noisy third-party loggers.
"""

import logging
import logging.handlers
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Imported from the submodule rather than the package: `app.utils.__init__`
# imports this module, so `from app.utils import redact` would resolve against
# a half-initialised package. See tests/test_imports.py for why import order is
# treated as a regression surface here.
from app.utils.redact import attach_to as attach_redaction

DEFAULT_LOG_RETENTION_DAYS = 14


def setup_logging(level: str = "DEBUG") -> None:
    """Configure the root logger.

    - logs/raggy.log — DEBUG and above, daily rotation, 14 days retention
    - stderr         — WARNING and above (keeps the terminal clean)

    Safe to call multiple times (idempotent).
    """
    from app.config import LOG_DIR

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.DEBUG)
    root.setLevel(numeric_level)

    # Idempotency: skip if a TimedRotatingFileHandler is already attached
    for h in root.handlers:
        if isinstance(h, logging.handlers.TimedRotatingFileHandler):
            return

    fmt_file = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt_console = logging.Formatter(
        fmt="[%(levelname)-8s] %(name)s — %(message)s"
    )

    # ── File handler ──────────────────────────────────────────────────────
    log_file = LOG_DIR / "raggy.log"
    fh = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt_file)
    fh.namer = lambda name: name
    root.addHandler(fh)

    # ── Console handler ───────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt_console)
    root.addHandler(ch)

    # ── Credential redaction ──────────────────────────────────────────────
    # On the handlers, not on the root logger: a logger-level filter does not
    # see records propagating up from child loggers, and every provider logs
    # through one. SECURITY.md promises keys are redacted from logs; this is
    # where that promise is kept for anything that reaches a file on disk.
    attach_redaction((fh, ch))

    # ── Suppress noisy third-party loggers ────────────────────────────────
    _QUIET = [
        "transformers", "sentence_transformers", "huggingface_hub",
        "urllib3", "httpx", "httpcore", "chromadb", "watchdog", "filelock",
        "pdfminer", "pdfminer.psparser", "pdfminer.pdfinterp",
        "pdfminer.pdfpage", "pdfminer.pdfdocument", "pdfminer.pdfdevice",
        "pdfminer.converter", "pdfminer.cmapdb", "pdfminer.layout",
        "pdfminer.image", "pdfplumber",
    ]
    for name in _QUIET:
        logging.getLogger(name).setLevel(logging.ERROR)

    logging.getLogger("raggy").info("Logging configured — output: %s", log_file)


def _is_log_file(path: Path) -> bool:
    """True for files this project writes as logs, and nothing else.

    The retention sweep is deliberately name-based rather than age-only:
    logs/ also holds tokens.db, the token-budget store, which must survive
    however old it gets.
    """
    name = path.name
    return name.endswith(".log") or name.endswith(".jsonl") or ".log." in name


def cleanup_old_logs(
    log_dir: Path,
    retention_days: int = DEFAULT_LOG_RETENTION_DAYS,
    now: datetime | None = None,
) -> list[Path]:
    """Delete log files in *log_dir* older than *retention_days*.

    TimedRotatingFileHandler's own backupCount only prunes files it rotated
    itself in this process. It does not touch the JSONL transcripts, and it
    prunes nothing at all if the app is started fresh each day — which is how
    Banco is used. This sweep is what actually bounds the directory.

    Logs are the one place where a prompt typed in a client's room is written
    to disk, so retention is a confidentiality control, not housekeeping.

    Parameters
    ----------
    log_dir:
        Directory to sweep. Missing directories are not an error.
    retention_days:
        Files last modified before ``now - retention_days`` are removed.
    now:
        Reference time, for tests. Defaults to the current UTC time.

    Returns
    -------
    list[Path]
        The files that were removed, in no particular order. Files that could
        not be removed are skipped rather than raising: log cleanup must never
        be the reason a lesson fails to start.
    """
    log_dir = Path(log_dir)
    if not log_dir.is_dir():
        return []

    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    cutoff = reference - timedelta(days=retention_days)

    removed: list[Path] = []
    for path in log_dir.iterdir():
        if not path.is_file() or not _is_log_file(path):
            continue
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if modified >= cutoff:
                continue
            path.unlink()
        except OSError:
            logging.getLogger("raggy").warning("Could not remove old log %s", path)
            continue
        removed.append(path)

    return removed
