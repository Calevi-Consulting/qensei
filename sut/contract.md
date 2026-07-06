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
| `source.path` | *(optional)* dir holding the backend SOURCE the design + diagnostics layers read (a clone, a generated contract, or — for the mock — the app itself). **Omit `source` entirely (or set `{"source": {"mode": "none"}}`) for a [sourceless SUT](#sourceless-suts)** — one whose backend source Qensei cannot read |
| `source.repo` | *(optional)* upstream git URL. When set, `make sync-source` (`engine/source_sync.py`) materialises `source.path` as a clone of it — how a SUT points at a real backend's source. Absent ⇒ the source is in-repo (mock/contract). A `source.path` that is a provisioned clone must be gitignored |
| `source.ref` | *(optional, with `source.repo`)* branch \| tag \| sha to check out (default: the repo's default branch) |
| `source.depth` | *(optional, with `source.repo`)* shallow clone depth (default `1`; `0` = full clone) |
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

## Sourceless SUTs

A SUT MAY be **sourceless** — Qensei cannot read its backend source (no OpenAPI/clone is available),
yet a running instance is reachable. Declare it by **omitting `source`** (or `{"source": {"mode":
"none"}}`). Then:

- `SUTConnector.has_source` is `False`; `source_module()` / `source_path()` are unavailable.
- **The live runtime still backs the regression gate** — cases run against `runtime.base_url` exactly
  as for any remote SUT. A sourceless SUT MUST use `runtime.mode: "remote"` (an `in_process` mock *is*
  its own source — the connector rejects that combination with a clear error).
- **`design` and `diagnostics` fall back to the ticket + docs.** Without `ROUTES` / `BUSINESS_RULES`,
  `design` reports only what the packs cover (no backend-surface gap analysis) and `diagnostics` returns
  `INDETERMINATE` — the contract of record is the ticket, so REAL_BUG vs TEST_BUG cannot be decided
  mechanically. The source-freshness gate is a no-op.

The contract authority then lives in the ticket (`ticket/contract.md`) and the SUT's `skills/` docs.
See `specs/002-sourceless-ticket-driven-mode.md`.

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
   For a **real** backend, set `source.repo` (+ `ref`), gitignore that `source.path`, and run
   `make sync-source SUT=sut/<name>` to clone/refresh the source before design/diagnostics read it.
   For a **sourceless** SUT, omit `source` from both the `mkdir` and the manifest, set
   `runtime.mode: "remote"`, and skip this step — design falls back to the ticket + docs and diagnose
   returns `INDETERMINATE` (see § Sourceless SUTs above; `sut/widget-api/` is the worked example).
3. Scaffold a pack INTO the site: `python scripts/new_pack.py --sut sut/<name> <TICKET> <slug>`
   (writes `sut/<name>/packs/<id>/` + `sut/<name>/specs/<id>.md`). Its case calls `sut.get/post`.
4. Run the site's gate — it discovers only THIS site's packs:
   `python -m engine.run --sut sut/<name>` (or `make test SUT=sut/<name>`). CI validates every
   site, and a single chosen site on demand (see `.github/workflows/` / `.gitlab-ci.yml`).

`sut/mock-shop/` (in_process mock), `sut/restful-booker/` (in_process mock + a `live` remote env, a
`plugin.py`, the cookie-login provider), and `sut/widget-api/` (a **sourceless** remote SUT — no
`source`; the ticket + `skills/` are the contract of record) are the worked examples to copy — and to
**delete** once your own SUTs exist (see below).

## Replacing the shipped example SUTs

`mock-shop`, `restful-booker`, `restful-booker-live`, and `widget-api` are **reference examples**.
A real adopter removes them (or keeps one as a live reference) once their own plugins exist.

**Auto-adapts — no edit needed** (all glob/`engine/sites.py`-discovered): the regression gate
(`engine/runner.py`), the UI lane (`engine/ui.py`), the design + diagnostics readers, the
deterministic gates (`fidelity_lint`, `coverage_lint`), the pytest **site bridges**
(`tests/test_sites.py`, `tests/test_ui.py`), and **both CI site matrices**
(`.github/workflows/qa-gate.yml`, `.gitlab-ci.yml`). Drop in a new `sut/<name>/` and these pick it up;
delete one and they stop running it. The false-green guard (exit `2` on "no cases discovered") keeps
an empty `sut/` from looking green.

**Must be updated by hand** (these reference an example SUT by name):

| What | Where | Action on removal |
|---|---|---|
| Makefile demo/diagnose defaults | `Makefile` (`SUT ?=`, `REALBUG_PACK`, `TESTBUG_PACK`, `SERVE_APP`, `demo-booker`) | Repoint at one of your SUTs, or ignore if you do not use the `demo`/`diagnose-*`/`serve` targets |
| Example-coupled framework tests | `tools/tests/test_multisite.py`, `test_sourceless.py`, `test_source_sync.py` | These assert on the shipped plugins — adapt to your SUTs or remove; they are examples, not core |
| Durable-state isolation | `tests/conftest.py` (`QAF_MOCK_STATE`, `QAF_BOOKER_STATE`) | A mock with **durable** state needs its own env line to stay isolated under `pytest -n auto` |
| Narrative docs | `docs/walkthrough.md`, `docs/design-coverage.md`, `docs/delivered-regressions.md`, `README.md` | These narrate `mock-shop` / `SHOP-456`; update or drop the references |

Nothing under `engine/` or `policies/` is on this list — the seam holds. Note the `--sourceless`
`widget-api` and any `remote` SUT are **not** in the default offline gate (they need live creds/env);
run them with `QAF_SITES=sut/<name>` (+ `--env`). Scaffold your own with
`make new-sut SUT=sut/<name> [SOURCELESS=1]`.
