"""
Logging configuration for Raggy.

Call setup_logging() once at app startup. Writes DEBUG+ to rotating daily log
files in logs/, WARNING+ to console. Suppresses noisy third-party loggers.
"""

import logging
import logging.handlers
from pathlib import Path


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
