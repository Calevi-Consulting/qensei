"""Credential resolution + auth-header injection — the generic seam.

t-800's ``lib/credentials.py`` + ``lib/vault.py`` resolve a token (direct value wins,
then a provider fills the gap) and the API client injects it on every request. Here
the same seam is product-neutral: the plugin's ``manifest["creds"]`` declares HOW to
authenticate; this module turns that + the uncommitted :class:`~engine.config.Settings`
into the headers :class:`~engine.sut.SUTConnector` adds to every request.

Modes (``creds.mode``):

  * ``none``      — no auth (the mock). Returns ``{}``.
  * ``token``     — bearer token from ``QAF_TOKEN`` (settings), header
                    ``Authorization: <scheme> <token>`` (scheme defaults to ``Bearer``).
  * ``userpass``  — HTTP Basic from ``QAF_USERNAME``/``QAF_PASSWORD``.
  * ``provider``  — delegate to a plugin callable ``sut/<name>/plugin.py:resolve_creds``
                    (this is where a Vault / AWS-SM integration plugs in WITHOUT touching
                    the engine — the generic equivalent of t-800's Vault client, which is
                    correctly plugin-side).

Precedence: a direct value in Settings always wins; the provider only fills gaps.
"""
from __future__ import annotations


class CredentialError(RuntimeError):
    """Raised when a backend declares auth but no credential can be resolved."""


def resolve_auth_headers(creds: dict, settings, provider=None) -> dict:
    """Return the auth headers to merge into every request, or ``{}`` for no-auth.

    :param creds: the manifest ``creds`` block (``{"mode": ...}``).
    :param settings: a :class:`~engine.config.Settings` (direct values win).
    :param provider: optional ``callable(settings) -> dict`` from the plugin, used for
        ``mode == "provider"`` (and as a fallback filler for token/userpass).
    """
    mode = (creds or {}).get("mode", "none")

    if mode == "none":
        return {}

    if mode == "token":
        token = settings.token or _from_provider(provider, settings).get("token")
        if not token:
            raise CredentialError(
                "creds.mode=token but no token resolved (set QAF_TOKEN or supply a provider)"
            )
        scheme = (creds.get("scheme") or "Bearer").strip()
        header = creds.get("header") or "Authorization"
        return {header: f"{scheme} {token}".strip()}

    if mode == "userpass":
        filled = _from_provider(provider, settings)
        user = settings.username or filled.get("username")
        pwd = settings.password or filled.get("password")
        if not user or pwd is None:
            raise CredentialError(
                "creds.mode=userpass but username/password not resolved "
                "(set QAF_USERNAME/QAF_PASSWORD or supply a provider)"
            )
        import base64

        raw = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        return {"Authorization": f"Basic {raw}"}

    if mode == "provider":
        if provider is None:
            raise CredentialError(
                "creds.mode=provider but the plugin exposes no resolve_creds(settings)"
            )
        headers = _from_provider(provider, settings).get("headers")
        if not headers:
            raise CredentialError("plugin resolve_creds() returned no 'headers'")
        return headers

    raise CredentialError(f"unknown creds.mode {mode!r}")


def _from_provider(provider, settings) -> dict:
    if provider is None:
        return {}
    result = provider(settings)
    return result if isinstance(result, dict) else {}
