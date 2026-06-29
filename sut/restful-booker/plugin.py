"""restful-booker plugin hooks — the OPTIONAL ``sut/<name>/plugin.py`` the engine calls when present.

This is where site-specific behaviour plugs in WITHOUT editing engine/ (the same way a real
product plugin, e.g. ``sut/acme``, would). The booker ships two hooks:

  * ``REQUIREMENTS`` — pre-flight checks the target env must satisfy (engine/preflight.py).
    ``rooms_available`` lets the booking packs SKIP (partial) rather than hard-fail when a
    target environment has no rooms to book.
  * ``resolve_creds`` — the real cookie-auth login, used only when creds.mode == "provider"
    (set per-run with QAF_CREDS_MODE=provider). The platform authenticates writes with a
    ``token`` cookie obtained from POST /auth/login; this performs that login and returns the
    Cookie header the connector adds to every request. The offline mock needs no auth, so the
    default gate never calls this — it is the seam that makes the ``live`` env usable.
"""
from __future__ import annotations

import json
import urllib.request

from engine.credentials import CredentialError

# The plugin's own knowledge of its real endpoint (mirrors manifest env.live.base_url), used
# as the login target when no explicit base_url/QAF_BASE_URL is supplied for a `live` run.
# The real platform serves its API under /api (a Next.js front-door); the bare host is the UI.
LIVE_URL = "https://automationintesting.online/api"


def _has_rooms(sut) -> bool:
    status, body = sut.get("/room/")
    return status == 200 and bool((body or {}).get("rooms"))


REQUIREMENTS = {
    "rooms_available": _has_rooms,
}


def resolve_creds(settings, base_url: str | None = None) -> dict:
    """Log in to the platform and return the ``token`` cookie as an auth header.

    Precedence for the login target: explicit ``base_url`` -> QAF_BASE_URL -> the known live
    URL. Credentials default to the platform's documented ``admin``/``password`` and are
    overridable with QAF_USERNAME / QAF_PASSWORD. Returns ``{"headers": {"Cookie": ...}}``.
    """
    target = (base_url or settings.base_url or LIVE_URL).rstrip("/")
    user = settings.username or "admin"
    pwd = settings.password if settings.password is not None else "password"
    payload = json.dumps({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(
        f"{target}/auth/login", data=payload, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": settings.user_agent},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            # The token may arrive either as a Set-Cookie (classic cookie-auth) or in the JSON
            # body ({"token": ...} — the current live API and the mock both do this). Try both.
            token = _token_from_cookies(r.headers.get_all("Set-Cookie") or [])
            if not token and raw:
                token = (json.loads(raw) or {}).get("token")
    except Exception as e:  # noqa: BLE001 - any login failure is a credential failure here
        raise CredentialError(f"restful-booker login failed against {target}: {e!r}") from e
    if not token:
        raise CredentialError(f"restful-booker login returned no token from {target}")
    return {"headers": {"Cookie": f"token={token}"}}


def _token_from_cookies(set_cookie_headers) -> str | None:
    for header in set_cookie_headers:
        for part in header.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "token" and value:
                return value
    return None
