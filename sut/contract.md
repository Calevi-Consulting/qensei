# SUT plugin contract — "backend access"

A System-Under-Test plugin is a directory under `sut/<name>/` that gives the
framework uniform access to one product under test. It is the seam that makes the
framework domain-agnostic: the engine, design, and diagnostics layers depend only
on this contract, never on a specific product. `sut/mock-shop/` is the reference
implementation; `sut/aiq/` would wrap the AttackIQ platform the same way.

## Required: `manifest.json`

| key | meaning |
|-----|---------|
| `name` | plugin id |
| `source.path` | dir holding the backend SOURCE the design + diagnostics layers read (a clone, a generated contract, or — for the mock — the app itself) |
| `runtime.mode` | `in_process` (framework boots `source/<app>` via `factory`) or `remote` (`runtime.base_url`) |
| `runtime.app` / `runtime.factory` | for `in_process`: the module + zero-arg factory returning a started HTTP server |
| `env` | named environments / base URLs |
| `creds` | how to resolve auth (the mock uses `none`; a real plugin resolves a token from env/Vault) |
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

The connector exposes `get(path)` / `post(path, body)` returning `(status, json)` and starts/stops
the runtime (`start(**kwargs)` / `stop()`, also a context manager). The `**kwargs` reach the
in-process factory — the mock uses `buggy=` to seed a regression for the diagnostics demo; a real
plugin ignores them.

## Adding a new SUT

1. `mkdir sut/<name>/{source,skills,learnings}` and write `manifest.json`.
2. Point `source` at the backend (clone or contract) and expose `ROUTES` + `BUSINESS_RULES`
   (or adapt `engine/design.py` + `engine/diagnostics.py` to your source representation).
3. Write packs under `packs/` whose cases call `sut.get/post`; run `python -m engine.run --sut sut/<name>`.
