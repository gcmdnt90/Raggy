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

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
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

# Time-to-live for cached results (seconds). Successful lists remain fresh for
# an hour. Failures use a shorter window so provider outages are retried while
# still preventing every page load from repeating the same failed call.
CACHE_TTL = 3600
FAILURE_CACHE_TTL = 300


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    created_at: float
    models: tuple[str, ...]
    live: bool


_CACHE_SALT = secrets.token_bytes(32)
_cache: dict[tuple[str, str], _CacheEntry] = {}


def credential_cache_key(credential: str) -> str:
    """Return a process-local fingerprint without retaining the credential."""
    return hashlib.sha256(_CACHE_SALT + credential.encode("utf-8")).hexdigest()


def _key(provider: str, cache_key: str | None) -> tuple[str, str]:
    return provider, cache_key or "default"


def _is_fresh(entry: _CacheEntry) -> bool:
    ttl = CACHE_TTL if entry.live else FAILURE_CACHE_TTL
    return (time.monotonic() - entry.created_at) < ttl


def fallback(provider: str) -> list[str]:
    """Return a copy of the static fallback list for ``provider``."""
    return list(FALLBACK_MODELS.get(provider, []))


def clear_cache(provider: str | None = None) -> None:
    """Drop cached live results (all providers, or just one)."""
    if provider is None:
        _cache.clear()
    else:
        for key in [key for key in _cache if key[0] == provider]:
            _cache.pop(key, None)


def is_live(provider: str, *, cache_key: str | None = None) -> bool:
    """Return whether the current cached list came from the provider API."""
    entry = _cache.get(_key(provider, cache_key))
    return bool(entry and _is_fresh(entry) and entry.live)


def cached(provider: str, *, cache_key: str | None = None) -> tuple[list[str], bool] | None:
    """Return a fresh cached catalog and its provenance, if one exists."""
    entry = _cache.get(_key(provider, cache_key))
    if not entry or not _is_fresh(entry):
        return None
    return list(entry.models), entry.live


def discover(
    provider: str,
    fetch_fn: Callable[[], list[str]],
    *,
    cache_key: str | None = None,
) -> list[str]:
    """Return live models for ``provider``, falling back to the static list.

    Parameters
    ----------
    provider:
        Provider key, e.g. ``"anthropic"``.
    fetch_fn:
        Zero-argument callable that performs the live API query and returns a
        list of model IDs. Any exception it raises is swallowed and the static
        fallback list is returned instead.

    Results are cached per provider and credential fingerprint. Failed
    discoveries are cached briefly as fallbacks so reactive UI reruns do not
    repeatedly hit the same unavailable endpoint.
    """
    key = _key(provider, cache_key)
    entry = _cache.get(key)
    if entry and _is_fresh(entry):
        return list(entry.models)

    try:
        models = fetch_fn()
        if models:
            models = sorted(set(models))
            _cache[key] = _CacheEntry(time.monotonic(), tuple(models), True)
            return list(models)
        logger.info("Live model discovery for %s returned nothing; using fallback", provider)
    except Exception as exc:
        logger.info(
            "Live model discovery failed for %s (%s); using fallback list",
            provider,
            type(exc).__name__,
        )

    models = fallback(provider)
    _cache[key] = _CacheEntry(time.monotonic(), tuple(models), False)
    return models
