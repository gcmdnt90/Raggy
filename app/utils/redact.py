"""Remove credentials from text before it is streamed, rendered or logged.

SECURITY.md promises that participant keys are "redacted from logs, and never
rendered by the harness". Nothing enforced that, and the provider SDKs make it
easy to break by accident:

* ``google-genai`` authenticates with the key as a ``?key=`` query parameter,
  and ``APIError`` stringifies to ``f"{code} {status}. {details}"`` where
  ``details`` is the raw response body.
* OpenAI's 401 body echoes the key it rejected, partially masked.

Both reach ``LLMError(str(exc))``, and from there ``app/server/runner.py`` puts
them in a ``pane_failed`` event that the harness prints on the projected
surface. `app/server/preflight.py` already says that a fragment on a screen
which has been projected is still a fragment of a real key; this module is what
lets the boundaries act on that rather than trusting each SDK to redact its own
errors.

Redaction happens at the boundary, not at the raise site: a provider cannot
know whether its message is about to be logged, shown to one trainer, or put in
front of a client's staff, and there is more than one SDK to keep honest.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping

__all__ = ["PLACEHOLDER", "RedactingFilter", "redact", "secret_values"]

PLACEHOLDER = "[redacted]"

#: The shortest value worth scrubbing by exact match. Below this, a configured
#: value is as likely to be an ordinary word appearing in the message, and
#: redacting it would destroy the error a trainer needs to read.
_MIN_SECRET_LENGTH = 8

#: Field names whose values are credentials. Used to pick the values worth
#: scrubbing out of a provider's constructor arguments while leaving
#: ``base_url`` alone — the egress host is precisely what PROJECT.md invariant 4
#: requires the room to be shown.
_SECRET_FIELD_HINTS = ("key", "token", "secret", "password", "credential")

#: Each pattern either captures the harmless prefix in group 1 and the secret
#: after it, or matches the secret alone. Written to over-match rather than
#: under-match: an over-redacted error still tells a trainer which provider
#: failed and why, and that is the trade this file exists to make.
_PATTERNS: tuple[re.Pattern[str], ...] = (
    # A key carried in a URL query string. This is the one that actually fires:
    # it is how google-genai authenticates.
    re.compile(r"(?i)([?&](?:key|api[_-]?key|access[_-]?token|token)=)[^&\s\"'<>]+"),
    # Header forms, as they appear when a transport quotes the request it sent.
    re.compile(
        r"(?i)((?:authorization|x-api-key|x-goog-api-key|api[_-]?key)\s*[\"']?\s*[:=]\s*\"?)"
        r"[^\s,;}\"'<>]+"
    ),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"),
    # Provider key shapes. `sk-` is matched loosely on purpose, because OpenAI
    # returns the rejected key partly masked and a masked fragment is still a
    # fragment of a real key.
    re.compile(r"sk-[^\s,;}\"'<>]{6,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{10,}"),
    re.compile(r"AQ\.[0-9A-Za-z_\-]{10,}"),
    re.compile(r"hf_[0-9A-Za-z]{10,}"),
    re.compile(r"gh[pousr]_[0-9A-Za-z]{10,}"),
)


def _substitute(match: re.Match[str]) -> str:
    return f"{match.group(1)}{PLACEHOLDER}" if match.groups() else PLACEHOLDER


def redact(text: object, *secrets: str | None) -> str:
    """Return ``text`` as a string with credentials removed.

    Parameters
    ----------
    text:
        Anything; it is stringified first, so an exception can be passed
        directly.
    secrets:
        Exact values known to be credentials, typically the keys this call was
        made with. These are scrubbed in addition to the patterns, which is
        what catches a key an SDK embeds in a shape nobody anticipated.
    """
    out = str(text)

    # Longest first, so a key that contains another configured value as a
    # substring is not half-replaced into an unrecognisable state.
    for secret in sorted(
        {s for s in secrets if s and len(s) >= _MIN_SECRET_LENGTH}, key=len, reverse=True
    ):
        out = out.replace(secret, PLACEHOLDER)

    for pattern in _PATTERNS:
        out = pattern.sub(_substitute, out)

    return out


def secret_values(mapping: Mapping[str, object] | None) -> tuple[str, ...]:
    """The string values in *mapping* whose field names mark them as credentials.

    ``app.server.sources.provider_kwargs`` returns ``{"api_key": ...}`` for an
    API provider and ``{"base_url": ...}`` for Ollama. Only the first is a
    secret; redacting the second would blank the egress host out of exactly the
    error where a trainer needs to see it.
    """
    if not mapping:
        return ()
    return tuple(
        value
        for name, value in mapping.items()
        if isinstance(value, str) and any(hint in name.lower() for hint in _SECRET_FIELD_HINTS)
    )


class RedactingFilter(logging.Filter):
    """Scrub every record on its way out to a handler.

    Attached to handlers rather than to a logger: a filter on a logger is not
    applied to records propagating up from its children, and almost every
    record here comes from a child of the root.

    Tracebacks are rendered here, redacted, and cached on the record. A
    formatter reuses ``exc_text`` when it is already set, so the unredacted
    exception is never formatted downstream.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: redact(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(
                    redact(value) if isinstance(value, str) else value for value in record.args
                )

        if record.exc_info and not record.exc_text:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))

        return True


def attach_to(handlers: Iterable[logging.Handler]) -> None:
    """Put a redacting filter on each handler, at most once."""
    for handler in handlers:
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(RedactingFilter())
