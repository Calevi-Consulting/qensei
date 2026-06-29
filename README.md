# qa-framework

A generic, backend-aware QA framework: a hybrid of **test-case design**, **automated
regression**, and **failure diagnostics**, governed by a reusable set of QA policies.
Domain-agnostic — it works against any product through a System-Under-Test plugin.

> Provisional name. It generalises the pattern behind two AttackIQ-specific tools —
> a manual-QA context agent (test-case design + domain knowledge) and a REST regression
> framework (automation + diagnostics) — and the reusable subset of a spec-driven
> methodology (the policies). Here those become product-neutral capabilities, and the
> product under test is a plugin. See [`docs/overview.md`](docs/overview.md).

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
make test              # gate: 2/2 pass against the healthy mock-shop
make diagnose-realbug  # seed a regression → lens says REAL_BUG (keep test red, file a bug)
make diagnose-testbug  # a wrong test → lens says TEST_BUG (fix the test, don't weaken the spec)
```

## The worked example (mock-shop)

`sut/mock-shop/` is a toy shop backend (products / cart / checkout with a 10%-off-at-3-items
rule). It is the reference SUT plugin that proves the framework is domain-agnostic: the same
engine runs `SHOP-123` (cart total) and `SHOP-456` (bulk discount) against it, and the
diagnostics lens tells a seeded regression of the discount rule (REAL_BUG) apart from a test
that asserts the wrong rate (TEST_BUG) — by reading the backend source. Swap in `sut/aiq/` and
nothing in `engine/`, `core/`, or `policies/` changes.

## Layout

```
policies/   general, QA-applicable policies (spec phases, ownership, test philosophy,
            security review, release safety, communication, git) — product-neutral
engine/     the core: sut.py (backend access) · case.py · runner.py (gate) ·
            design.py (backend-aware design) · diagnostics.py (REAL_BUG vs TEST_BUG)
core/       specs/ (intent contracts, human-approved) · plans/ (implementation rationale)
packs/      the landed regressions (one dir per pack, a case.py + an index README)
sut/        SUT plugins (the "backend access" abstraction) + contract.md
            mock-shop/  source/ (the backend) · skills/ · learnings/ · manifest.json
examples/   diagnostics walkthroughs (e.g. an intentionally wrong test)
docs/       overview.md (architecture + lineage)
```

## Ownership (from the methodology)

Humans own intent: specs, acceptance criteria, scope, approvals. The framework owns
implementation: plans, packs, the engine. See [`policies/methodology.md`](policies/methodology.md).

## Status

v0 — runnable mock demo. The engine, the three capabilities, and the SUT-plugin seam are real
and exercised end-to-end against `mock-shop`. Next: a second SUT plugin to validate the seam,
and the manual-validation + ticket→spec handoff legs.
