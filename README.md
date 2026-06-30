# qa-framework

A generic, backend-aware QA framework: a hybrid of **test-case design**, **automated
regression**, and **failure diagnostics**, governed by a reusable set of QA policies.
Domain-agnostic — it works against any product through a System-Under-Test plugin.

> Provisional name. It unifies three QA capabilities that usually live in separate tools —
> manual-QA test-case design (with domain knowledge), automated REST regression, and failure
> diagnostics — under one product-neutral engine, governed by a reusable set of development
> policies, with the product under test wired in as a plugin. See [`docs/overview.md`](docs/overview.md).

## What it does (three capabilities, one backend connection)

All three need access to the backend under test — its **source** (to design cases and to
diagnose failures) and its **runtime** (to execute cases). That shared dependency is the
spine; see the [SUT contract](sut/contract.md).

| Capability | What it does | Try it |
|-----------|--------------|--------|
| **Design** | reads the backend surface (endpoints + business rules) and reports coverage gaps + candidate cases | `make design` |
| **Regress** | runs the pack suite against a live backend — the deterministic gate | `make test` |
| **Diagnose** | classifies a failure as **REAL_BUG** vs **TEST_BUG** by reading the backend contract | `make diagnose-realbug` / `make diagnose-testbug` |

## Quickstart

No dependencies — pure Python 3 standard library (the mock backend, the HTTP client, and the
engine's own runner are all stdlib). Boots the mock backend in-process.

```bash
make demo      # design report → regression gate → REAL_BUG demo → TEST_BUG demo
```

Or individually:

```bash
make design            # backend-aware coverage report
make test              # gate: 3/3 pass against the healthy mock-shop
make diagnose-realbug  # seed a regression → lens says REAL_BUG (keep test red, file a bug)
make diagnose-testbug  # a wrong test → lens says TEST_BUG (fix the test, don't weaken the spec)
```

## Development setup

The **runtime above needs no install** — `make demo` / `make test` run on pure Python 3 stdlib.
The **dev/test toolchain** (parallel test runner + linter + CVE scanner) is managed with
[Poetry](https://python-poetry.org/) and installed into a project-local `.venv`:

```bash
make install   # poetry install: pytest, pytest-xdist, ruff, pip-audit (into ./.venv)
```

If Poetry is missing, `make install` prints how to get it (`pipx install poetry`, or the official
installer). It pins the **latest** published versions as the baseline and uses Python 3.14. Then:

```bash
make pytest    # run the whole suite under pytest + xdist, in parallel  (pytest -n auto)
make lint      # ruff lint
make cve       # pip-audit dependency CVE scan
make verify    # full local CI: lint + cve + pytest + fidelity + secrets
```

Tests live in two places: **`tools/tests/`** is the zero-dependency `unittest` suite (engine +
seam tests — what `make check` runs on the bare stdlib), and **`tests/`** is the pytest
**site-integration bridge** that runs every site's regression packs as parallel pytest cases. Pick a
site with `QAF_SITES` (CI uses this to validate one chosen site), or a lane with a marker:

```bash
QAF_SITES=sut/restful-booker poetry run pytest tests/test_sites.py   # one site's packs
poetry run pytest tests/test_sites.py -m smoke                        # the smoke lane
```

CI runs **lint + CVE scan + tests** on every push, and the site gate is **site-selectable** (a
GitHub Actions dropdown / a GitLab `SITE` variable). `make check` stays dependency-free (stdlib
`unittest` + fidelity + secrets) for environments without Poetry. See
[`scripts/install.sh`](scripts/install.sh) and the `[tool.poetry]` / `[tool.ruff]` /
`[tool.pytest.ini_options]` blocks in [`pyproject.toml`](pyproject.toml).

## Working on different sites

A **site** is a SUT plugin under `sut/<name>/`. Each site is **self-contained** — it owns its
backend access *and* its tests (packs / specs / tickets) — so the framework tests tickets of
one site or another by pointing `--sut` at it:

```bash
make test SUT=sut/mock-shop        # the toy shop's regressions
make test SUT=sut/restful-booker   # the hotel-booking site's regressions
```

The gate for one site never discovers another's cases: the engine defaults `--packs` to the
selected SUT's own `packs/` dir. CI fans the gate over every site; all must be green.

## The worked examples (two sites)

- **`sut/mock-shop/`** — a toy shop backend (products / cart / checkout with a 10%-off-at-3-items
  rule). The reference plugin: the same engine runs `SHOP-123` (cart total) and `SHOP-456` (bulk
  discount), and the diagnostics lens tells a seeded regression of the discount rule (REAL_BUG)
  apart from a test that asserts the wrong rate (TEST_BUG) — by reading the backend source.
- **`sut/restful-booker/`** — a faithful zero-dependency mock of mwinteringham's
  [restful-booker-platform](https://github.com/mwinteringham/restful-booker-platform)
  (live at [automationintesting.online](https://automationintesting.online)): auth / rooms /
  bookings, the **real "no double-booking" (409)** rule, and an illustrative long-stay discount
  for the same diagnosable REAL_BUG/TEST_BUG seam. Ships a `live` env (the real API under `/api`)
  that points the same plugin at the public site to exercise the remote + cookie/token-login seam
  (`QAF_ENV=live`). `make demo-booker` runs its full offline walkthrough.

That a *second*, differently-shaped site drops in with **no change to `engine/` or `policies/`**
is what proves the SUT seam is genuinely generic.

## Two testing approaches: REST and UI

The framework supports **both** functional-testing surfaces over the same SUT plugin:

- **REST** — a `RegressionCase` (`engine/case.py`) calls the JSON API through the `SUTConnector`
  (`sut.get` / `sut.post`). Fast, deterministic — the default gate. Packs live in `sut/<name>/packs/`.
- **UI** — a `UICase` (`engine/ui.py`) drives the site's web UI in a **real browser** with
  **Playwright** (`run(self, page, base_url, expect)`). End-to-end through the front-end. Packs live
  in `sut/<name>/ui-packs/`; the site declares where its UI is served via `ui.path` in the manifest.

```bash
make pytest     # REST + unit tests (the fast default lane)
make test-ui    # the browser (Playwright) UI packs — headless
make ui-watch   # WATCH the UI verification live — a headed, slowed-down browser
```

The worked example is `sut/restful-booker/ui-packs/BOOK-UI-1-book-a-room/` — it books a room through
the booking **form** (fill, pick a room, submit, assert the confirmation), the UI counterpart to the
REST `BOOK-1` pack. The `/test-ticket` command can verify a ticket over REST or UI (headed, so a QA
person watches), and `/spec-test` turns that result into a REST **or** a UI automated pack accordingly.
UI tests are a separate opt-in lane (a browser is slower/heavier than the REST gate).

## Layout

```
policies/   general, QA-applicable policies (spec phases, ownership, test philosophy,
            security review, release safety, communication, git) — product-neutral
engine/     the core: sut.py (backend access) · case.py · runner.py (gate) ·
            design.py (backend-aware design) · diagnostics.py (REAL_BUG vs TEST_BUG)
sut/        the SITES under test — one self-contained plugin dir each + contract.md.
            Each owns everything for its site:
              mock-shop/       source/ · skills/ · learnings/ · packs/ · specs/ ·
                               tickets/ · examples/ · manifest.json
              restful-booker/  the same shape (+ plugin.py · ui-packs/ for the Playwright
                               UI tests) for automationintesting.online
ticket/     the tracker-agnostic ticket-provider contract + jira config
            (a site's own tickets live under sut/<name>/tickets/)
docs/       overview.md (architecture + lineage)
```

## Ownership (from the methodology)

Humans own intent: specs, acceptance criteria, scope, approvals. The framework owns
implementation: plans, packs, the engine. See [`policies/methodology.md`](policies/methodology.md).

## Status

v0 — runnable mock demo. The engine, the three capabilities, and the SUT-plugin seam are real
and exercised end-to-end against **two** sites: `mock-shop` and `restful-booker`. The second
site validates that the seam is genuinely generic (it dropped in with no change to `engine/` or
`policies/`). Next: the manual-validation + ticket→spec handoff legs, and a real authenticated
backend behind the `live`-env path the booker plugin demonstrates.
