"""Model discovery: live provider model lists with a cached static fallback.

Live discovery is the *primary* source — each provider queries its own
``/models`` endpoint at runtime, so newly released models appear automatically
and retired ones disappear. The curated ``FALLBACK_MODELS`` lists are only a
backstop, used when the API is unreachable or no API key is configured.

Fallback IDs verified against provider documentation in June 2026. They will
drift over time; that is acceptable because live discovery normally supersedes
them.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)

# Backstop lists (used only when live discovery is unavailable).
FALLBACK_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    ],
    "openai": [
        "gpt-5",
        "gpt-5-mini",
        "gpt-4o",
        "gpt-4o-mini",
        "o4-mini",
    ],
    "google": [
        "gemini-3.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ],
}

# Time-to-live for cached live results (seconds). A short TTL keeps the list
# fresh without hammering the provider on every Streamlit rerun.
CACHE_TTL = 3600

_cache: dict[str, tuple[float, list[str]]] = {}


def fallback(provider: str) -> list[str]:
    """Return a copy of the static fallback list for ``provider``."""
    return list(FALLBACK_MODELS.get(provider, []))


def clear_cache(provider: str | None = None) -> None:
    """Drop cached live results (all providers, or just one)."""
    if provider is None:
        _cache.clear()
    else:
        _cache.pop(provider, None)


def discover(provider: str, fetch_fn: Callable[[], list[str]]) -> list[str]:
    """Return live models for ``provider``, falling back to the static list.

    Parameters
    ----------
    provider:
        Provider key, e.g. ``"anthropic"``.
    fetch_fn:
        Zero-argument callable that performs the live API query and returns a
        list of model IDs. Any exception it raises is swallowed and the static
        fallback list is returned instead.

    Results are cached per provider for ``CACHE_TTL`` seconds.
    """
    entry = _cache.get(provider)
    if entry and (time.monotonic() - entry[0]) < CACHE_TTL:
        return list(entry[1])

    try:
        models = fetch_fn()
        if models:
            models = sorted(set(models))
            _cache[provider] = (time.monotonic(), models)
            return list(models)
        logger.warning("Live model discovery for %s returned nothing; using fallback", provider)
    except Exception:
        logger.warning("Live model discovery failed for %s; using fallback list", provider, exc_info=True)

    return fallback(provider)
