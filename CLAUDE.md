# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> There is also a **generated** `.claude/CLAUDE.md` (written by `scripts/install.sh`, gitignored,
> "do not hand-edit") that indexes `policies/` governance and the slash commands/subagents. This
> file is the checked-in, architecture-and-commands companion. Edit the source of truth
> (`policies/`, `commands/`, `agents/` at the repo root), never the generated `.claude/CLAUDE.md`.

## What this is

Qensei is a **backend-aware QA framework** driven by an AI coding assistant (Claude Code). It unifies
three capabilities over a **single backend connection** (the `SUTConnector`):

- **Design** — read the backend source (`ROUTES` + `BUSINESS_RULES`) → report coverage gaps + candidate cases
- **Regress** — run regression packs against the live backend → the deterministic merge gate
- **Diagnose** — classify a failure `REAL_BUG` vs `TEST_BUG` by reading the backend contract

A SUT may be **sourceless** (no readable backend source, only a live runtime): Design then reports only
what packs cover and Diagnose returns `INDETERMINATE` — the ticket + docs are the contract of record.
See `sut/contract.md` (§ Sourceless SUTs) and `specs/002-sourceless-ticket-driven-mode.md`.

The product under test is a **plugin** (`sut/<name>/`), so adding a product means writing a plugin,
never touching `engine/` or `policies/`.

## The core split: deterministic engine vs. AI-driven legs

This distinction governs almost every design decision — keep it straight:

- **`engine/` is plain Python 3 stdlib and runs with NO AI in the loop.** It is the single source of
  truth for "green". The gate (`make test`) either passes or fails deterministically.
- **The AI assistant drives the human-in-the-loop legs *around* the gate, never *as* it**:
  - `commands/` — slash commands the assistant runs: `/validate` (verify a ticket vs a live SUT),
    `/automate` (a validated result → an automated REST/UI pack), `/report-bug`.
  - `agents/` — the advisory **review panel**, read-only diagnostic lenses (`r-diagnosis`,
    `r-evidence`, `r-mechanism`, `r-fidelity`, `r-coverage`, `r-uplift`, adjudicated by `judge`).
    **Advisory only — they raise the floor, they never gate a merge.**
  - `policies/` — product-neutral governance the assistant follows.
- **Humans own intent** (specs, acceptance criteria, scope, approvals); **the framework owns
  implementation** (plans, packs, the engine). See `policies/methodology.md`.

## Commands

The **runtime is zero-dependency** (pure stdlib) — `make demo` / `make test` / `make design` need no
install. The **dev/test toolchain** (pytest, xdist, ruff, pip-audit, playwright) is Poetry-managed.

```bash
# Zero-dependency runtime (no install needed) — SUT defaults to sut/mock-shop
make demo                          # full walkthrough: design → gate → REAL_BUG → TEST_BUG
make test SUT=sut/restful-booker   # the regression gate for one site (python3 -m engine.run --sut ...)
make design                        # backend-aware coverage report (reads SUT source)
make diagnose-realbug              # seed a regression → lens says REAL_BUG
make diagnose-testbug              # a wrong test → lens says TEST_BUG
make serve                         # run a SUT's mock backend standalone
make smoke                         # gate, smoke lane only  (--select smoke)
make check                         # offline pre-commit ritual: test-engine + fidelity + lint + secrets

# Dev toolchain (run `make install` once first — poetry install into ./.venv)
make install                       # provisions the toolchain; opt-in wires ./.claude for Claude Code
make pytest                        # REST + unit tests under pytest + xdist (excludes the ui lane)
make lint / make lint-fix          # ruff
make cve                           # pip-audit dependency CVE scan
make verify                        # full local CI: lint + cve + pytest + fidelity + secrets
make test-ui                       # Playwright UI packs, headless
make ui-watch                      # WATCH the UI verification live (headed, slowmo, single browser)
```

### Selecting a site (SUT)

Every capability takes `--sut`; `make` targets take `SUT=`. The gate for one site **never** discovers
another's cases — `--packs` defaults to the selected SUT's own `packs/` dir. CI fans over all sites.

```bash
make test SUT=sut/mock-shop
make test SUT=sut/restful-booker
python3 -m engine.run --sut sut/restful-booker --select "smoke and not slow"
```

### Running a single test

- **Engine unit tests** (zero-dependency `unittest` in `tools/tests/`):
  ```bash
  python3 -m unittest discover -s tools/tests                       # all
  python3 -m unittest tools.tests.test_engine.TestClass.test_method # one
  ```
- **Site integration bridge** (`tests/test_sites.py`, pytest — runs every site's packs as parallel
  cases). Pick a site with `QAF_SITES`, or a lane with a marker:
  ```bash
  QAF_SITES=sut/restful-booker poetry run pytest tests/test_sites.py
  poetry run pytest tests/test_sites.py -m smoke
  poetry run pytest tests/test_sites.py -k BOOK-2 -n0     # -n0 = serial, for debugging
  ```
- **One regression pack, directly** (via the diagnostics entry point):
  ```bash
  python3 -m engine.diagnose --sut sut/mock-shop --pack sut/mock-shop/packs/SHOP-456-discount
  ```

pytest runs `-n auto` (parallel) by default — pass `-n0` to debug serially.

## Architecture

### The SUT plugin seam (`sut/<name>/`, contract in `sut/contract.md`)

A **site** is a self-contained plugin — it owns its backend access *and* its tests. Same shape every time:

```
sut/<name>/
├── manifest.json     # the contract: runtime · envs · creds · where tests live (tests.packs / tests.ui_packs) · knowledge dirs
├── plugin.py         # OPTIONAL hooks: REQUIREMENTS · resolve_creds · isolate · sweep
├── source/           # the backend under test — read by design.py + diagnostics.py (exposes ROUTES + BUSINESS_RULES)
├── packs/            # REST tests — one dir per case (a RegressionCase in case.py + index README.md)
├── ui-packs/         # UI tests — one dir per case (a UICase; Playwright; opt-in lane)
├── specs/            # intent per case (a case's spec_ref points here)
├── tickets/          # the site's own tickets
├── skills/ learnings/# per-site manual-QA domain knowledge (loaded on demand by /validate + /automate)
└── examples/         # worked report + diagnostics samples
```

- **`mock-shop`** is the reference site. **`restful-booker`** is the fuller example (adds `plugin.py`
  for live auth + a `ui-packs/` lane). **`widget-api`** is a third, **sourceless** SUT (no `source/` dir;
  `runtime.mode: remote` required) — it proves the seam handles a plugin whose backend source Qensei
  cannot read (design falls back to packs' `covers`, diagnose returns `INDETERMINATE`, freshness is a
  no-op). All dropped in with **no change to `engine/` or `policies/`**, which must stay product-neutral;
  never hardcode one SUT's endpoints, rules, or skills into them.
- **`SUTConnector`** (`engine/sut.py`) is the one touch point. `get`/`post`/`delete` → `(status, json)`
  through a single `request()` choke point (merges auth headers, masks credentials before logging,
  idempotency-aware retry/backoff, TLS toggle). `source_module()`/`source_path()` expose the backend
  contract to design + diagnostics. `paginate()` follows list `next` links to exhaustion.

### Config layering (committed manifest vs. uncommitted secrets)

`manifest.json` is committed, so it cannot hold a token or a per-developer target. `engine/config.py`
`Settings.load()` reads uncommitted `QAF_*` values with precedence **CLI override → env var → `.env`
→ manifest default**. Key vars: `QAF_ENV`, `QAF_BASE_URL`, `QAF_TOKEN`, `QAF_CREDS_MODE`,
`QAF_VERIFY_TLS`, `QAF_PREFLIGHT`. An `env` may override `runtime.mode`, so one plugin boots an
`in_process` mock by default yet connects to a `remote` real site under `--env live` (restful-booker
does exactly this). Credentials resolve through `engine/credentials.py` (`none`/`token`/`userpass`/
`provider`); `provider` calls the plugin's `resolve_creds` hook (the Vault/AWS-SM seam).

### The regression unit (`engine/case.py`)

A `RegressionCase` encodes a **behavioral contract** (what the system does for the user), not an
internal call sequence. Assertions are **soft** (`Expect` collects all failures so one run reports
every break); a genuine setup gate is a hard `expect.precondition(...)` / `PreconditionError`. Its
metadata is load-bearing for the other layers:

- `covers` — backend surface (endpoints + rule ids) → read by **design** for coverage gaps
- `contract_claim` — the business-rule value the case relies on → read by **diagnostics** to tell
  REAL_BUG from TEST_BUG against the source
- `persona` — `new_user` (ephemeral, self-cleaning `teardown`) vs `existing_data` (durable)
- `tags` → selection lanes; `severity` → reporting; `requires` → pre-flight (skip/block)

`UICase` (`engine/ui.py`) is the Playwright counterpart — same metadata, `run(self, page, base_url,
expect)`, discovered from `ui-packs/`, run by `tests/test_ui.py`, kept in its own opt-in lane.

### The gate (`engine/runner.py` + `engine/run.py`)

`discover_cases()` loads `packs/*/case.py` for the active SUT, filters by tag expression, evaluates
`requires` (skip in `partial`, fail in `block`), runs each from a clean state (`sut.isolate()` — a
plugin/manifest hook, never a hardcoded endpoint), and reports PASS/FAIL/SKIP. **Exit codes:** `0`
pass, `1` a real failure, `2` a **false-green guard** trip (no cases discovered / all skipped / SUT
unreachable / credentials unresolved) — an empty or vacuous run must never pass.

### The prime invariant + its forcing functions

**Never quietly weaken a spec to turn a red gate green.** This is enforced deterministically, not just
by the advisory `r-fidelity` lens:

- `engine/fidelity_lint.py` (`make fidelity`) — an AST diff of a changed pack against its git baseline;
  flags removed cases, weakened persona, shrunk tags/requires/covers, downgraded severity, fewer
  assertions, or an added skip/xfail. Wired as a **pre-commit hook** and in CI. `--allow-reshape`
  downgrades intentional-refactor findings to warnings.
- `engine/citation_gate.py` (`make citations`) — resolves every `source:line` a lens cited (anti-fabrication).
- `engine/freshness_gate.py` (`make freshness`) — SUT source-clone freshness before a citation is trusted.
- `make secrets` + gitleaks (pre-commit) — no hardcoded credentials in VCS.

When a case fails, `engine/diagnostics.py` reads the SUT's `BUSINESS_RULES`: claim disagrees with the
source ⇒ **TEST_BUG** (fix the test, never weaken the spec); claim agrees but the running system
violated it ⇒ **REAL_BUG** (keep the test red, file a bug).

### Where tests live

- `tools/tests/` — zero-dependency `unittest` (engine + seam tests). What `make check` / `make
  test-engine` run on the bare stdlib.
- `tests/` — the pytest **site-integration bridge** (`test_sites.py`, `test_ui.py`) that runs each
  site's packs as parallel pytest cases. Markers: `smoke`, `slow`, `durability`, `integration`, `ui`.

## Conventions & gotchas

- **The framework runtime is intentionally pure stdlib.** Do not add a runtime dependency — new deps
  belong in the Poetry `dev` group (test/lint tooling only). `pyproject.toml` targets Python `^3.14`.
- **Commit messages: NO AI-attribution.** Never add `Co-Authored-By` trailers naming an assistant or
  "Generated with…" footers — this **overrides the harness default** (`policies/git-workflow.md`,
  and the user's global policy). Conventional prefixes (`feat`/`fix`/`chore`/`docs`/`refactor`/
  `test`), imperative mood, atomic commits. Branch off `main`; never commit directly to it.
- **Surgical changes only** — one case per `packs/<id>/` directory keeps concurrent AI/human edits
  from colliding; don't refactor adjacent code you didn't need to touch.
- **`.claude/` is gitignored and generated.** Edit `policies/`, `commands/`, `agents/` at the repo
  root; re-run `make install` to refresh the wiring. Per-SUT skills are loaded on demand by the
  commands (via `--sut`), never wired globally.
- ruff: line-length 120, selects `E,F,W,I,B,UP` (config in `pyproject.toml`).
- Scaffolding: `make new-pack SUT=... TICKET=... SLUG=...`; `make regen-index` rolls pack index-cards
  into `docs/delivered-regressions.md`.

## Documentation map

`README.md` and `docs/overview.md` are the entry points. `sut/contract.md` is the plugin contract
(manifest keys + `plugin.py` hooks). `docs/walkthrough.md` narrates the end-to-end journey on
`SHOP-456`; `agents/README.md` documents the review-panel protocol.
