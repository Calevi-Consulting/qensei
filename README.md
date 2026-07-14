# Qensei

A generic, backend-aware QA framework: a hybrid of **test-case design**, **automated
regression**, and **failure diagnostics**, governed by a reusable set of QA policies.
Domain-agnostic — it works against any product through a System-Under-Test plugin.

> **Qensei** = *Q* (QA) + *sensei*: an AI coding assistant (Claude Code) drives it like a QA sensei,
> reading the backend to design cases and diagnose failures. The **deterministic engine** (`engine/`,
> `make test`) is plain Python 3 stdlib and is the single source of truth for "green"; the assistant
> drives the human-in-the-loop legs **around** that gate, never as it. Humans own intent (specs,
> acceptance criteria, approvals); the framework owns implementation. Full framing:
> [`docs/overview.md`](docs/overview.md).

## New here? Start with the tour

- **[The teaching deck](docs/qensei-teaching-deck.pdf)** — a 15-slide guided tour: the problem, the
  mental model, the `/validate` → `/automate` → `/report-bug` workflow, and the ownership model.
- **[The walkthrough](docs/walkthrough.md)** — the same story on a runnable example (`SHOP-456`):
  ticket → `/validate` evidence → `/automate` spec + pack → the gate → REAL_BUG vs TEST_BUG.

## What it is (three capabilities, one backend connection)

Qensei is **driven by an AI coding assistant** ([Claude Code](https://claude.com/claude-code)): the
assistant runs the human-in-the-loop legs — slash commands (`commands/`: `/validate`, `/automate`,
`/report-bug`) and an advisory, read-only review panel (`agents/`), under product-neutral governance
(`policies/`). The **deterministic core runs with no AI**: `engine/` + `make test` are the gate. All
three capabilities share one dependency — access to the backend's **source** (to design + diagnose)
and its **runtime** (to execute); that seam is the [SUT contract](sut/contract.md). A SUT can also be
**sourceless** (a live runtime, no readable source): Design reports what packs cover and Diagnose
returns `INDETERMINATE`, the ticket being the contract of record ([sourceless SUTs](sut/contract.md#sourceless-suts)).

```
     ┌──────── AI coding assistant · human-in-the-loop (advisory) ────────┐
     │  /validate    /automate    /report-bug    review panel (agents/)   │
     └────────┬───────────┬─────────────┬──────────────┬─────────────────┘
              ▼           ▼             ▼              ▼
   ╔══════════════════════════════════════════════════════════════════════╗
   ║  engine/  —  deterministic · pure stdlib · THE SOURCE OF TRUTH FOR    ║
   ║  "green"        make test → PASS / FAIL        (no AI in the loop)    ║
   ╚═══════════════════════════════╤══════════════════════════════════════╝
                                   ▼  one connection · SUTConnector
                         ┌──────────────────────┐
                         │ SUT plugin sut/<name> │  in-process mock  OR
                         │ source + runtime      │  live backend (STAGING/prod)
                         └──────────────────────┘
```

| Capability | What it does | Try it |
|-----------|--------------|--------|
| **Design** | reads the backend surface (endpoints + business rules) and reports coverage gaps + candidate cases ([how it's used](docs/design-coverage.md)) | `make design` |
| **Regress** | runs the pack suite against a live backend — the deterministic gate | `make test` |
| **Diagnose** | classifies a failure as **REAL_BUG** vs **TEST_BUG** by reading the backend contract | `make diagnose-realbug` / `make diagnose-testbug` |

For the full mental model (diagrams, execution model), see [`docs/overview.md`](docs/overview.md).

## Quickstart

No dependencies — pure Python 3 standard library. Boots the mock backend in-process.

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

The runtime above needs **no install**. The dev/test toolchain (test runner + linter + CVE scanner)
is [Poetry](https://python-poetry.org/)-managed into a project-local `.venv`:

```bash
make install   # poetry install: pytest, pytest-xdist, ruff, pip-audit (into ./.venv)
make pytest    # the whole suite under pytest + xdist, in parallel
make lint      # ruff lint
make cve       # pip-audit dependency CVE scan
make verify    # full local CI: lint + cve + pytest + fidelity + coverage-lint + secrets
```

The **regression tests themselves** are the packs inside each plugin —
`sut/<name>/packs/<id>/case.py` (REST) and `sut/<name>/ui-packs/` (UI); `tests/` is only a pytest
**bridge** that discovers and runs them as parallel cases. The **framework's own** tests are separate:
`tools/tests/` (zero-dependency `unittest` — engine + seam tests, what `make check` runs). `make
install` can also opt-in wire the framework into Claude Code (see [`scripts/install.sh`](scripts/install.sh));
the CI, gates, and site selection are detailed in [`docs/quality-gates.md`](docs/quality-gates.md).

## Sites & worked examples

A **site** is a SUT plugin under `sut/<name>/`; each is self-contained (its own backend access +
tests), so the gate for one site never discovers another's:

```bash
make test SUT=sut/mock-shop        # the toy shop's regressions
make test SUT=sut/restful-booker   # the hotel-booking site's regressions
```

A site either **boots an in-process mock** (offline, deterministic — the demos' default) or **runs
against a live deployed backend** (STAGING / prod) via `runtime.mode: remote` + creds/env; one plugin
can do both — a mock by default, the real site under `--env live` (as `restful-booker` does). Details:
[`docs/remote-backend.md`](docs/remote-backend.md).

The shipped sites (`mock-shop`, `restful-booker`, the sourceless `widget-api`) are **replaceable
reference examples** — a real adopter swaps in their own (`make new-sut`). The catalog, how to add
your own, and what to touch when removing them live in [`sut/README.md`](sut/README.md); the plugin
shape (manifest keys + hooks) is in [`sut/contract.md`](sut/contract.md).

## REST and UI lanes

Two functional surfaces over the same plugin:

- **REST** — a `RegressionCase` (`engine/case.py`) calls the JSON API via the `SUTConnector`. Fast,
  deterministic — the default gate. Packs in `sut/<name>/packs/`.
- **UI** — a `UICase` (`engine/ui.py`) drives the web UI in a **real browser** with Playwright. Packs
  in `sut/<name>/ui-packs/` (an opt-in lane; a browser is slower than the REST gate).

```bash
make test-ui    # the browser (Playwright) UI packs — headless
make ui-watch   # WATCH the UI verification live — a headed, slowed-down browser
```

`/validate` verifies a ticket over REST or UI; `/automate` produces a REST **or** UI pack accordingly.
See [`docs/quality-gates.md`](docs/quality-gates.md) and [`docs/ticket-testing-and-reporting.md`](docs/ticket-testing-and-reporting.md).

## Documentation map

Start at **[`docs/overview.md`](docs/overview.md)** — the documentation map (thesis, execution model,
layers on disk, how the pieces compose). Then:

- [`sut/README.md`](sut/README.md) — the SUT plugins (replaceable examples) + how to add your own
- [`sut/contract.md`](sut/contract.md) — the plugin shape: manifest keys + `plugin.py` hooks
- [`docs/architecture.md`](docs/architecture.md) · [`docs/regression-gate.md`](docs/regression-gate.md) · [`docs/quality-gates.md`](docs/quality-gates.md) · [`docs/walkthrough.md`](docs/walkthrough.md)

Top-level orientation (one gloss each): `commands/` assistant legs · `agents/` review panel ·
`policies/` governance · `engine/` the deterministic core · `sut/` the sites · `ticket/` tracker
contract · `docs/`.

## Status

v0 — runnable mock demo. The engine, the three capabilities, and the SUT-plugin seam are exercised
end-to-end against **three** sites: `mock-shop` and `restful-booker` (source-backed) and the
sourceless `widget-api`, which dropped in with no change to `engine/` or `policies/`. `/validate` and
`/automate` have shipped. Fuller status: [`docs/overview.md`](docs/overview.md#status--next).

## License

[MIT](LICENSE) © 2026 Martin Hereu.
