# Walkthrough — from a manually-tested ticket to a permanent regression

A narrated end-to-end pass through the methodology on one concrete, runnable example:
**SHOP-456**, the mock-shop bulk-discount ticket. No prior experience with the framework is
assumed. For the slide version of this story, see the
[teaching deck](qensei-teaching-deck.pdf); for the reference docs, start at
[overview.md](overview.md).

> **`mock-shop` / `SHOP-456` are a reference example** — they exist to make this story runnable. A
> real adopter replaces them with their own SUT plugin (`make new-sut`; see
> [`sut/README.md`](../sut/README.md)); the methodology below is identical for your product.

The journey has four stops:

```
ticket  →  /validate (manual leg)  →  /automate (spec + pack)  →  the gate (make test)
                                                                      ↓ on a later failure
                                                             DIAGNOSE: REAL_BUG vs TEST_BUG
```

The slash commands run inside the AI assistant (Claude Code); the gate and the diagnostics
engine are plain Python with no AI in the loop.

## Stop 0 — the ticket

[`sut/mock-shop/tickets/SHOP-456.md`](../sut/mock-shop/tickets/SHOP-456.md) is a JIRA-style
story served by the `mock-file` ticket provider: *checkout gives 10% off when the cart holds
3 or more items*. It carries four acceptance criteria — no discount below the threshold, 10%
at or above it, the threshold is **inclusive** (exactly 3 qualifies — the off-by-one guard),
and `total = subtotal − discount`.

It is money, and it has a threshold: both sides of the boundary need checking, not just
"a big cart gets a discount". That observation is recorded as a learning in
[`sut/mock-shop/learnings/SHOP_LEARNINGS.md`](../sut/mock-shop/learnings/SHOP_LEARNINGS.md),
and the framework loads it before touching the ticket.

## Stop 1 — `/validate`: check the ticket against the live system

```
/validate SHOP-456 --sut mock-shop
```

The manual-validation leg ([`commands/validate.md`](../commands/validate.md)). Each acceptance
criterion becomes a check against the **live** SUT — here over REST, through the
`SUTConnector` (`sut.post("/cart", …)`, `sut.post("/checkout")`); criteria that only exist in
a front-end run in a real browser (Playwright), headed, so the QA person watches the
verification live.

Outcomes per check (PASS / FAIL / SKIPPED / BLOCKED) are written back to the ticket behind an
approval gate, and the run is saved as a **run report** — `runs/SHOP-456_<TIMESTAMP>.md` — with
the evidence and a note of which checks ran over REST vs UI. That report is the durable
source of truth the next stop consumes.

## Stop 2 — `/automate`: lock the validated result in as a regression

```
/automate SHOP-456 --sut mock-shop
```

The automation leg ([`commands/automate.md`](../commands/automate.md)) turns the validated
result into two durable artifacts:

- **The spec** — [`sut/mock-shop/specs/SHOP-456-bulk-discount.md`](../sut/mock-shop/specs/SHOP-456-bulk-discount.md):
  intent only (context, requirements, testable acceptance criteria, persona coverage,
  risks). Human-approved before any code is written — humans own the *what* and the *why*.
- **The pack** — [`sut/mock-shop/packs/SHOP-456-discount/`](../sut/mock-shop/packs/SHOP-456-discount/case.py):
  a self-contained `RegressionCase` plus its index-card `README.md`. Agent-implemented — the
  framework owns the *how*.

The **surface follows the verification**: criteria validated over REST become a REST pack;
criteria validated through the UI become a Playwright pack. SHOP-456 was verified over REST,
so the pack calls the same two endpoints the manual pass exercised, and pins **both sides of
the boundary**:

```python
covers = ["POST /checkout", "bulk-discount"]
contract_claim = {"rule": "bulk-discount", "rate": 0.10, "min_qty": 3}

# qty 2 → discount 0.0, total 20.0   (below the threshold)
# qty 3 → discount 3.0, total 27.0   (at the threshold — the off-by-one guard)
```

`covers` and `contract_claim` are not decoration: they name the route and the business rule
the case protects, which is what lets the diagnostics layer (Stop 4) reason about a failure
instead of guessing.

## Stop 3 — the gate: deterministic green

```
make test SUT=sut/mock-shop
```

The regression gate ([regression-gate.md](regression-gate.md)) runs every pack of the selected
site against the live backend and exits non-zero on any failure. Zero dependencies, no AI in
the loop — the gate is the only thing that decides pass or fail. The assistant designs,
validates, and diagnoses *around* it; it never becomes it.

From this point on, SHOP-456 is permanent coverage: every future run re-asserts the discount
rule at both sides of the threshold.

## Stop 4 — when it fails later: REAL_BUG vs TEST_BUG

A red case has two possible causes, and they demand opposite reactions. The DIAGNOSE
capability classifies the failure by reading the backend contract — both demos are runnable:

```
make diagnose-realbug   # seeds a regression of the discount rule → REAL_BUG
make diagnose-testbug   # a test asserting the wrong rate         → TEST_BUG
```

- **REAL_BUG** — the backend no longer honours the rule the case protects. Keep the test red
  and file a structured, human-gated defect with `/report-bug`
  ([`sut/mock-shop/examples/reports/SHOP-456-bug.md`](../sut/mock-shop/examples/reports/SHOP-456-bug.md)
  is a worked example).
- **TEST_BUG** — the test itself is wrong. Fix the test — **never weaken the spec to turn it
  green** (the fidelity lint and the advisory [review panel](multiagent/review-panel.md)
  exist to catch exactly that move).

## What to notice

- **One artifact chain, fully traceable**: ticket → run report → spec → pack → gate report.
  Every automated assertion traces back to a criterion a human approved.
- **Ownership stays split**: humans own intent (the spec), the framework owns implementation
  (the pack), the deterministic gate owns "green".
- **The manual pass is not throwaway work** — `/validate`'s evidence is precisely what
  `/automate` converts into permanent coverage. (`/automate` can also start from a ticket validated
  *outside* Qensei — it reads the ticket's `comments[]` for the manual evidence — so a prior `/validate`
  run is the common path, not a hard requirement.)

## Try it

```
make demo    # design report → regression gate → REAL_BUG demo → TEST_BUG demo
```

Runs offline on the in-process mock-shop backend, pure Python 3 stdlib — nothing to install.
