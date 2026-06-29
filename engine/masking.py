"""Secret masking at the logging boundary.

The rule (policies/input-hygiene.md, security-review.md) is: redact known credential
keys before anything is printed, logged, or folded into a failure detail. The policy
existed as prose with no enforcing code; this is the enforcing code. ``mask`` is
key-name based and product-neutral, so it lives in the engine core, not a plugin.
"""
from __future__ import annotations

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "password",
        "passwd",
        "secret",
        "client_secret",
        "cookie",
        "set-cookie",
        "x-api-key",
    }
)

REDACTED = "***REDACTED***"


def mask(value, _sensitive=SENSITIVE_KEYS):
    """Deep-copy ``value`` redacting any dict entry whose key looks sensitive.

    Works on nested dicts/lists; scalars pass through untouched. Header dicts and JSON
    request/response bodies both flow through here before being logged.
    """
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in _sensitive:
                out[k] = REDACTED
            else:
                out[k] = mask(v, _sensitive)
        return out
    if isinstance(value, list | tuple):
        return type(value)(mask(v, _sensitive) for v in value)
    return value
