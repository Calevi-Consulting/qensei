# DESIGN — the coverage-gap report (`make design`)

`make design` (`engine/design.py`) is the first of Qensei's three capabilities. It reads the
backend's declared surface from the SUT **source** and cross-references what the packs cover, to
report **coverage gaps** and candidate cases.

> The `mock-shop` source shown below is a **reference example**; the same `make design` reads YOUR
> SUT's source once you add a plugin (`make new-sut`; see [`sut/README.md`](../sut/README.md)).

It is **deterministic** — plain Python 3 stdlib, no AI, and no runtime (it reads source only). And it
is a **decision aid, not a code generator**: its output is read by a QA (or the AI assistant) who
decides what to build. Nothing pipes the report into test generation.

## What it reads, what it reports

- **From the source** (via `SUTConnector.source_module()`): `ROUTES` (endpoints) and `BUSINESS_RULES`
  (rule ids) — the backend's declared surface.
- **From the packs**: each `RegressionCase`'s `covers` declaration (the endpoints + rule ids it
  exercises), plus the UI packs.
- **The difference**: endpoints and rules the backend declares but no pack covers → gaps, each with a
  candidate-case suggestion.

```text
$ make design SUT=sut/mock-shop

  DESIGN report — backend surface of 'mock-shop' (read from .../sut/mock-shop/source/app.py)

  endpoints (8): GET /products, GET /products/{id}, POST /cart, GET /cart, POST /cart/clear,
                 POST /checkout, GET /accounts/{name}, POST /accounts
  business rules (1): bulk-discount
  covered by packs: GET /accounts/{id}, GET /cart, POST /accounts, POST /cart, POST /checkout,
                    bulk-discount
  COVERAGE GAPS — candidate cases to design:
    - endpoint not regressed: GET /products       -> propose a new_user case ...
    - endpoint not regressed: GET /products/{id}   -> propose a new_user case ...
    - endpoint not regressed: POST /cart/clear     -> propose a new_user case ...
    - endpoint not regressed: GET /accounts/{name} -> propose a new_user case ...
```

## A worked QA use case — find a gap, close it, confirm

The report's output is **not** an input to any generator. A QA (or the AI assistant) reads it and
decides what to build. The loop:

1. **Find the gaps** — `make design SUT=sut/mock-shop`. The engine reads the source, so nothing is
   missed by memory: here, four endpoints have no regression.
2. **Decide** — pick a gap to close, e.g. `GET /products/{id}` (product detail, plus its 404).
3. **Author the case** — this is where the report drives *action*:
   - *With the AI leg* — run `/automate` with the ticket, or a short description when there is none:
     `/automate "product detail returns 404 for a missing id"`. The agent reads the source
     (`GET /products/{id}` → 200 for a real id, 404 if missing) and the SUT's `skills/`, then authors
     `sut/mock-shop/packs/<id>-product-detail/case.py` — declaring `covers = ["GET /products/{id}"]`
     and the assertions. The report said *what is missing*; the agent designs the *case*, with
     judgment (the happy path **and** the 404).
   - *By hand* — `make new-pack SUT=sut/mock-shop TICKET=<id> SLUG=product-detail`, then write the
     `case.py`, declaring `covers = ["GET /products/{id}"]`.
4. **The loop closes through `covers`** — `design.py` reads each pack's `covers`. The new pack
   declares `covers=["GET /products/{id}"]`, so the *next* report counts it as covered. This shared
   `covers` ↔ `ROUTES` vocabulary is the only machine-level link between the report and the tests — a
   **coverage ledger**, not a generator.
5. **Confirm the closure** — `make design SUT=sut/mock-shop` again; `GET /products/{id}` has moved
   from a gap to *covered by packs*.
6. **The gate** — `make test SUT=sut/mock-shop` runs the new pack against the live backend. This is
   independent of the report; DESIGN never gates a merge.

```text
make design ──▶ a human/AI reads the gaps ──▶ /automate  (or  make new-pack) ──▶ case.py declares `covers`
     ▲                                                                                       │
     └──────────────── make design again: the gap now shows as covered ◀─────────────────────┘
```

## The `covers` ↔ `ROUTES` ledger — and a gotcha

Because the report matches each pack's `covers` **strings** against the source `ROUTES`, a mismatch
leaves a **phantom gap**. In the report above the source declares `GET /accounts/{name}`, but the
durability pack declares `covers = ["GET /accounts/{id}"]` (`{id}` vs `{name}`). So the report lists
`GET /accounts/{id}` under *covered* and still flags `GET /accounts/{name}` as an uncovered gap —
even though an accounts pack exists. A `covers` typo is **visible in the report, not silent**. The
[`r-coverage`](../agents/r-coverage.md) lens catches the same drift (it verifies `covers` /
`contract_claim` resolve to real `ROUTES` / `BUSINESS_RULES`).

## Sourceless SUTs

A **sourceless** SUT (no `source` — see [Sourceless SUTs](../sut/contract.md#sourceless-suts)) has no
`ROUTES` / `BUSINESS_RULES` to read, so `make design` cannot compute backend-surface gaps. It falls
back to reporting only what the packs cover and states the surface is defined by the ticket + docs.
Design there is authored from the ticket's acceptance criteria and the SUT's `skills/`, by the AI
leg — the deterministic report shrinks, the judgment-side design does not.

## Why the report does not generate the tests

Emitting test code straight from a coverage diff is exactly the **AI-test trap** the framework exists
to avoid: auto-generated tests tend to pass every mock-level check while silently failing the real
boundary. So DESIGN deliberately stops at *where* coverage is missing; a human owns intent and the AI
authors the case with domain judgment (personas, boundaries, the real-downstream assertion). The
report informs that work — it does not replace it.

## Related

- [`regression-gate.md`](regression-gate.md) — REGRESS, the deterministic gate (`make test`).
- [`diagnostics-and-review-panel.md`](diagnostics-and-review-panel.md) — DIAGNOSE.
- [`../commands/automate.md`](../commands/automate.md) — the `/automate` authoring flow.
- [`walkthrough.md`](walkthrough.md) — the end-to-end `SHOP-456` journey.
