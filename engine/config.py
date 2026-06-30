"""Settings — the UNCOMMITTED per-run config channel.

`manifest.json` is committed, so it cannot carry a secret token or a per-developer /
per-CI target choice. This layer reads those from the environment (and an optional,
gitignored `.env`) so the same committed plugin can be pointed at different
environments with different credentials without editing tracked files.

Precedence (highest first): explicit CLI override -> environment variable -> `.env`
file -> the plugin manifest default. Everything is read through `Settings.load()`.

Recognised variables (all optional, prefix ``QAF_``):

  QAF_ENV         name of the environment to select from manifest["env"]
  QAF_BASE_URL    override the resolved base_url outright (wins over env selection)
  QAF_TOKEN       the bearer token / API key for a `remote` authenticated backend
  QAF_USERNAME    basic-auth username (when creds.mode == "userpass")
  QAF_PASSWORD    basic-auth password
  QAF_CREDS_MODE  override the manifest's creds.mode for this run (none | token |
                  userpass | provider) — e.g. flip a mock's "none" to "provider" to
                  exercise a real login against the same plugin's `live` env
  QAF_USER_AGENT  override the request User-Agent. Defaults to a browser UA so a real
                  site's WAF / bot check (e.g. the public restful-booker demo behind
                  Cloudflare) does not 403 the stdlib client; in-process mocks ignore it
  QAF_VERIFY_TLS  "0"/"false" to disable TLS verification (self-signed onprem certs)
  QAF_PREFLIGHT   "partial" (skip unmet) or "block" (fail unmet); default "partial"

It layers a gitignored .env under live environment variables under explicit CLI
overrides, feeding both environment selection and the credential resolver — stdlib only.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PREFIX = "QAF_"

# A browser-like default UA so a real site fronted by a WAF / bot check (e.g. the public
# restful-booker demo behind Cloudflare) does not 403 the stdlib client. In-process mocks
# ignore it. Override per-run with QAF_USER_AGENT (e.g. an identifiable QA-tool UA on a site
# that allows it).
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def _load_dotenv(path: Path) -> dict[str, str]:
    """Minimal ``.env`` parser (KEY=VALUE per line; ``#`` comments; optional quotes)."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


@dataclass
class Settings:
    """Resolved per-run configuration (uncommitted overrides over manifest defaults)."""

    env: str | None = None
    base_url: str | None = None
    token: str | None = None
    username: str | None = None
    password: str | None = None
    creds_mode: str | None = None  # overrides manifest creds.mode when set
    user_agent: str = DEFAULT_USER_AGENT
    verify_tls: bool = True
    preflight: str = "partial"  # "partial" | "block"
    raw: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, dotenv: str | os.PathLike = ".env", overrides: dict | None = None) -> Settings:
        """Build settings from ``.env`` then the live environment, then CLI overrides.

        Live ``os.environ`` wins over ``.env`` (the .env is a developer default);
        explicit ``overrides`` (from the CLI) win over both.
        """
        merged: dict[str, str] = {}
        merged.update(_load_dotenv(Path(dotenv)))
        merged.update({k: v for k, v in os.environ.items() if k.startswith(PREFIX)})
        for k, v in (overrides or {}).items():
            if v is not None:
                merged[k if k.startswith(PREFIX) else PREFIX + k.upper()] = v

        def g(name: str) -> str | None:
            return merged.get(PREFIX + name)

        verify = g("VERIFY_TLS")
        return cls(
            env=g("ENV"),
            base_url=g("BASE_URL"),
            token=g("TOKEN"),
            username=g("USERNAME"),
            password=g("PASSWORD"),
            creds_mode=g("CREDS_MODE"),
            user_agent=g("USER_AGENT") or DEFAULT_USER_AGENT,
            verify_tls=(verify not in ("0", "false", "False", "no")) if verify is not None else True,
            preflight=(g("PREFLIGHT") or "partial"),
            raw=merged,
        )
