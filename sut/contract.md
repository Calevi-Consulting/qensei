# SUT plugin contract — "backend access"

A System-Under-Test plugin is a directory under `sut/<name>/` that gives the
framework uniform access to one product under test. It is the seam that makes the
framework domain-agnostic: the engine, design, and diagnostics layers depend only
on this contract, never on a specific product. `sut/mock-shop/` is the reference
implementation; `sut/acme/` would wrap a real product backend the same way.

## Required: `manifest.json`

| key | meaning |
|-----|---------|
| `name` | plugin id |
| `source.path` | dir holding the backend SOURCE the design + diagnostics layers read (a clone, a generated contract, or — for the mock — the app itself) |
| `tests.packs` / `tests.specs` / `tests.tickets` / `tests.ui_packs` | the plugin's OWN test assets (relative to `sut/<name>/`; default `packs`/`specs`/`tickets`/`ui-packs`). This is what makes a site **self-contained** — the gate for one site never discovers another's cases; `run.py` / `design.py` default `--packs` to the SUT's `packs_dir`. `ui_packs` holds the browser-driven `UICase` packs |
| `ui.path` | where the site serves its **web UI**, relative to the runtime base_url (e.g. `/ui`). Present ⇒ the site has a UI testing surface; the Playwright UI lane (`UICase` packs in `ui_packs`) drives `base_url + ui.path`. Absent ⇒ REST-only |
| `runtime.mode` | `in_process` (framework boots `source/<app>` via `factory`) or `remote` (`runtime.base_url`). A selected `env` MAY override this (see `env` below) |
| `runtime.app` / `runtime.factory` | for `in_process`: the module + zero-arg factory returning a started HTTP server |
| `runtime.isolate` | optional path POSTed before each case for a clean `new_user` state (e.g. `/cart/clear`, `/booking/reset`); the generic runner is product-neutral and never hardcodes an endpoint |
| `runtime.verify_tls` | optional `false` to skip TLS verification for a self-signed/onprem cert (also overridable per-run via `QAF_VERIFY_TLS=0`) |
| `env` | named environments → `{ "base_url": ..., "mode": ... }`, selected with `--env <name>` / `QAF_ENV` (see `engine/config.py`). An env MAY override `runtime.mode`, so one plugin boots an `in_process` mock by default yet connects to a `remote` real site under `--env live` (restful-booker does exactly this) |
| `creds` | how to resolve auth: `{"mode": "none" | "token" | "userpass" | "provider", ...}` — resolved by `engine/credentials.py` against the uncommitted `QAF_*` settings (`token` → `Authorization: <scheme> <token>`; `scheme`/`header` overridable; `provider` → the plugin's `resolve_creds`). The mode is overridable per-run with `QAF_CREDS_MODE` (e.g. flip a mock's `none` to `provider` to log in against the same plugin's `live` env) |
| `knowledge.skills` / `knowledge.learnings` | dirs of domain manual-QA context |

## What the framework expects from the SOURCE

Design and diagnostics read the backend's **declared contract**. The mock exposes it
as module-level data the connector imports:

- `ROUTES` — `(method, path, description)` triples → the surface `design` reports coverage over.
- `BUSINESS_RULES` — `{id, endpoint, description, ...params}` → the rules `diagnostics` checks a
  failing case's `contract_claim` against to decide REAL_BUG vs TEST_BUG.

For a real backend these can come from an OpenAPI spec, a parsed clone, or a hand-maintained
contract file — the connector's `source_module()` / `source_path()` are the only touch points,
so the representation is a plugin detail.

## Runtime access

The connector exposes `get(path)` / `post(path, body)` / `delete(path)` returning `(status, json)` and
starts/stops the runtime (`start(**kwargs)` / `stop()`, also a context manager). The `**kwargs` reach the
in-process factory — the mock uses `buggy=` to seed a regression for the diagnostics demo; a real plugin
ignores them. Every request goes through one `request()` choke point that: merges the resolved auth
headers, masks credentials before any log, retries transient gateway/connection errors with backoff
(idempotency-aware: a `GET` retries `504`, a write does not), and honours the TLS toggle. A
`paginate(first_path, items_of, next_of)` helper follows a list endpoint's `next` link to exhaustion so
existence/idempotency checks don't false-negative as the backend's data grows.

## Optional `sut/<name>/plugin.py` — hooks the engine calls when present

A plugin MAY ship a `plugin.py` exposing any of these (all optional; the mock ships none):

| hook | signature | used by |
|------|-----------|---------|
| `REQUIREMENTS` | `dict[str, callable(sut) -> bool]` | `engine/preflight.py` — per-case `requires=[...]` keys the target env must satisfy (skip/block). The engine always provides `platform_reachable`. |
| `resolve_creds` | `callable(settings) -> {"headers": {...}}` or `{"token"/"username"/"password": ...}` | `engine/credentials.py` for `creds.mode == "provider"` (the seam where Vault / AWS-SM plugs in WITHOUT touching the engine) |
| `isolate` | `callable(sut)` | `SUTConnector.isolate()` — custom clean-state reset (overrides `runtime.isolate`) |
| `sweep` | `callable(sut, max_age_s, dry_run) -> list` | `SUTConnector.sweep_ephemerals()` — reap orphaned `qaf-ephemeral:` objects left by crashed runs |

## Uncommitted per-run configuration

`manifest.json` is committed, so secrets and per-developer / per-CI choices live in the environment
(prefix `QAF_`) or an optional gitignored `.env`, read by `engine/config.py` (`Settings.load()`):
`QAF_ENV`, `QAF_BASE_URL`, `QAF_TOKEN`, `QAF_USERNAME`/`QAF_PASSWORD`, `QAF_VERIFY_TLS`, `QAF_PREFLIGHT`.
Precedence: CLI flag > env var > `.env` > manifest default.

## Adding a new SUT (a new site)

1. `mkdir sut/<name>/{source,skills,learnings,packs,specs,tickets}` and write `manifest.json`.
2. Point `source` at the backend (clone or contract) and expose `ROUTES` + `BUSINESS_RULES`
   (or adapt `engine/design.py` + `engine/diagnostics.py` to your source representation).
3. Scaffold a pack INTO the site: `python scripts/new_pack.py --sut sut/<name> <TICKET> <slug>`
   (writes `sut/<name>/packs/<id>/` + `sut/<name>/specs/<id>.md`). Its case calls `sut.get/post`.
4. Run the site's gate — it discovers only THIS site's packs:
   `python -m engine.run --sut sut/<name>` (or `make test SUT=sut/<name>`). CI validates every
   site, and a single chosen site on demand (see `.github/workflows/` / `.gitlab-ci.yml`).

`sut/mock-shop/` (in_process mock) and `sut/restful-booker/` (in_process mock + a `live` remote
env, a `plugin.py`, the cookie-login provider) are the two worked examples to copy.
