"""Network target validation.

Banco is distributed to workshop participants and, from M5, runs an agent on
their machines. Any base URL that reaches ``requests`` therefore has to be
checked before it is used, not after: an unvalidated host is a server-side
request forgery primitive, and the most valuable target is usually not a
public site but a link-local metadata endpoint such as 169.254.169.254.

See SECURITY.md, "Banco's second threat model".
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

__all__ = ["normalize_ollama_base_url"]

_ALLOWED_SCHEMES = frozenset({"http", "https"})

# Hostnames that are loopback by definition rather than by address.
_LOOPBACK_NAMES = frozenset({"localhost"})


def _is_loopback_host(host: str) -> bool:
    """True if *host* can only ever resolve to this machine.

    Name-based hosts are not resolved: DNS is attacker-influenced and a lookup
    here would be a time-of-check/time-of-use gap. Only the literal names that
    are loopback by specification are accepted.
    """
    if host.lower() in _LOOPBACK_NAMES:
        return True

    # urlsplit strips the brackets from an IPv6 literal, so `host` is bare here.
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def normalize_ollama_base_url(url: str, *, allow_remote: bool = False) -> str:
    """Validate an Ollama base URL and return it in canonical form.

    Accepts only http/https URLs pointing at loopback, with no embedded
    credentials, and returns the URL without its trailing slash.

    Parameters
    ----------
    url:
        The candidate base URL, typically ``OLLAMA_BASE_URL`` from ``.env``.
    allow_remote:
        Permit a non-loopback host. Off by default. A remote Ollama means
        every prompt in the room leaves this machine, so the egress indicator
        must show it and the trainer must have chosen it deliberately.

    Returns
    -------
    str
        The normalized URL, e.g. ``http://localhost:11434``.

    Raises
    ------
    ValueError
        If the URL is empty, uses a scheme other than http/https, carries
        credentials, omits a host, or names a non-loopback host while
        ``allow_remote`` is false. The message names the offence, because it
        surfaces during pre-flight where a trainer has to act on it.
    """
    if not url or not url.strip():
        raise ValueError("Ollama base URL is empty.")

    parsed = urlsplit(url.strip())

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Ollama base URL must use http or https, got {parsed.scheme or 'no'} "
            f"scheme in {url!r}."
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "Ollama base URL must not embed credentials. Remove the "
            "user:password@ part; Ollama does not use them, and they would be "
            "written to .env and to logs."
        )

    host = parsed.hostname
    if not host:
        raise ValueError(f"Ollama base URL has no host: {url!r}.")

    if not allow_remote and not _is_loopback_host(host):
        raise ValueError(
            f"Ollama base URL must point at this machine, got host {host!r}. "
            "Loopback only (localhost, 127.0.0.1, ::1). A remote host would "
            "send every prompt off this machine."
        )

    # Rebuild from validated parts rather than trusting the input string, and
    # drop the trailing slash so callers can append "/api/..." unconditionally.
    netloc = f"[{host}]" if ":" in host else host
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"

    path = parsed.path.rstrip("/")

    return f"{parsed.scheme}://{netloc}{path}"
