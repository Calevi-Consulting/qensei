# qa-framework — architecture & lineage

A map-level reference. Living document: update it when a capability, policy, or layer changes.

## Thesis

One backend-aware QA agent with three capabilities over a single backend connection:

```
        ┌──────────────── policies/ (general, QA-applicable) ────────────────┐
        │  spec phases · ownership · test philosophy · security · release    │
        └────────────────────────────────────────────────────────────────────┘
                                     governs
   ┌───────────┐        ┌───────────┐        ┌────────────────────┐
   │  DESIGN   │        │  REGRESS  │        │     DIAGNOSE       │
   │ read the  │        │ run packs │        │ REAL_BUG vs        │
   │ backend → │        │ vs live → │        │ TEST_BUG by        │
   │ propose   │        │ the gate  │        │ reading the source │
   │ cases     │        │           │        │                    │
   └─────┬─────┘        └─────┬─────┘        └─────────┬──────────┘
         │   source access    │  runtime access       │  source access
         └────────────────────┴───────────────────────┘
                          SUTConnector
                  (sut/<name>/ — the backend plugin)
```

Design and diagnostics need the backend **source**; regression needs the backend **runtime**.
Both go through one `SUTConnector`, so adding a product means writing a plugin, not touching the
core.

## Layers

- **`policies/`** — the product-neutral governance: the spec-driven phases, the ownership model
  (humans own intent; the framework owns implementation), test philosophy, security review,
  release-safety/reversibility, communication standards, git workflow. Derived from a general
  methodology and stripped of any single product's specifics.
- **`engine/`** — the core. `sut.py` (backend access), `case.py` (the soft-assert regression
  unit), `runner.py` (the deterministic gate), `design.py` (coverage from the backend surface),
  `diagnostics.py` (the REAL_BUG/TEST_BUG lens).
- **`core/specs` + `core/plans`** — intent contracts (human-approved) and implementation
  rationale, separated so intent changes go through human approval while plans iterate freely.
- **`packs/`** — the landed regressions, one directory each with a `case.py` and an index card.
- **`sut/`** — the plugins. `mock-shop/` is the reference; a real product (e.g. `aiq/`) is the
  same shape.

## The three capabilities

1. **Design** (`engine/design.py`) — reads `ROUTES` + `BUSINESS_RULES` from the backend source,
   cross-references the packs' `covers`, and reports the gap as candidate cases. The generic form
   of designing tests by reading the system, not guessing.
2. **Regress** (`engine/runner.py` + `run.py`) — discovers packs, runs each from a clean state
   against the live backend, and reports pass/fail with a non-zero exit for CI. The gate.
3. **Diagnose** (`engine/diagnostics.py` + `diagnose.py`) — on a failure, compares the case's
   `contract_claim` to the backend's declared contract and the runtime response:
   - claim agrees with the contract, runtime violated it → **REAL_BUG** (keep red, file a bug);
   - claim disagrees with the contract → **TEST_BUG** (fix the test; never weaken the spec);
   - the case threw → **ENV_OR_TRANSIENT**; no claim → **INDETERMINATE** (human adjudicates).

## Lineage (what it generalises)

This is the product-neutral extraction of three things:

| Source of the pattern | What it contributes here |
|----------------------|--------------------------|
| A manual-QA context agent (domain skills, learnings, test-case design) | the **DESIGN** capability + `sut/<name>/skills` + `learnings` |
| A REST regression framework (specs, packs, personas, the merge gate, the diagnostic review lenses) | the **REGRESS** + **DIAGNOSE** capabilities + `core/` + `packs/` |
| A spec-driven methodology | the **`policies/`** governance |

The single new idea binding them is that **one backend connection serves both test design and
diagnostics** — which is why "backend access" is the framework's central abstraction rather than
an incidental detail.

## Status & next

v0 runs the three capabilities end-to-end against `mock-shop`. Open next steps: a second SUT
plugin (validates the seam is really generic), the manual-validation leg (AI-driven validation
producing evidence), and the ticket→spec handoff that seeds a spec from a validation run.
