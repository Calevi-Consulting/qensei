# Plan — SHOP-456 bulk discount at the ≥3 threshold (REST, `new_user`)

- **Spec:** [`sut/mock-shop/specs/SHOP-456-bulk-discount.md`](../specs/SHOP-456-bulk-discount.md)
- **Ticket:** [`sut/mock-shop/tickets/SHOP-456.md`](../tickets/SHOP-456.md)
- **Pack:** [`sut/mock-shop/packs/SHOP-456-discount/`](../packs/SHOP-456-discount/) (already automated)
- **SUT:** `sut/mock-shop` — `runtime.mode: in_process` (the source ships in-repo and is always fresh);
  `runtime.isolate: POST /cart/clear` runs before each case.

> **Retro-plan.** This pack was authored before Qensei had a Phase-2b design panel. The plan is written
> after the fact, from the case as it stands, as the **spec-005 demonstrator**: the first real R-DESIGN
> run in this repo, and the first `## Design panel` record `engine/design_panel_lint.py` gates.

## REST mapping

Each manual step in the ticket, mapped to the SUTConnector call and confirmed against the SUT source
(`sut/mock-shop/source/app.py`, read via `SUTConnector.source_module()`):

| Manual step (ticket) | SUTConnector call | Source |
|---|---|---|
| Add 2 units of a product to an empty cart | `sut.post("/cart", {"product_id": 1, "qty": 2})` | `sut/mock-shop/source/app.py:41` (`POST /cart`) |
| Check out; expect `status == 201`, `discount ≈ 0.0`, `total ≈ 20.0` — the **literal** total under the stated subtotal (2 × 10.0); the case does not read `order["subtotal"]`, so the AC's identity `total = subtotal − discount` is entailed only under that assumption (Design panel F2) | `sut.post("/checkout")` → `(201, order)` | `sut/mock-shop/source/app.py:44` (`POST /checkout`) |
| Add 3 units (checkout cleared the cart) | `sut.post("/cart", {"product_id": 1, "qty": 3})` | `app.py:41` |
| Check out; expect `status == 201`, `discount ≈ 3.0` (10% of 30.0), `total ≈ 27.0` — again the literal total under subtotal 30.0 (Design panel F2) | `sut.post("/checkout")` → `(201, order)` | `app.py:44`; rule `app.py:62-66` (`bulk-discount`, `rate` = `DISCOUNT_RATE` `app.py:23`, `min_qty` = `DISCOUNT_MIN_QTY` `app.py:24`) |

Checkout is destructive — it clears the cart (`sut/mock-shop/source/app.py:150`) — which is why the second
boundary re-adds before checking out. **This is a precondition the case relies on but does not check**
(Design panel F3): if the clear regressed, the qty-3 add would land on a residual qty-2 cart, the discount
assertion would go red, and DIAGNOSE would attribute it to `bulk-discount` (claim = contract) although the
break is in checkout's side effect, which no rule id and no pack's `covers` names. The mechanism itself —
the clear is synchronous, inside the handler, before the response — is confirmed by R-MECHANISM (see the
Design panel record).

## Case shape

- One `RegressionCase` (`BulkDiscountApplies`), `persona = "new_user"`, `severity = "critical"`,
  `tags = {"smoke"}`.
- **Soft assertions** (`expect.equal` / `expect.approx`) on both boundaries in one `run()`, so a single
  gate run reports every break. No `requires` pre-flight: the case needs a reachable SUT (the gate's
  false-green guard checks that) **and** the checkout-clears-the-cart side effect between the two
  boundaries, which it currently trusts blind — both `POST /cart` responses are discarded too. The
  hardening R-DESIGN proposes (an `expect.precondition` on the emptied cart and on the add status — a
  `PreconditionError` is a FAIL, not a SKIP, and DIAGNOSE reports it as `PRECONDITION_FAILED` rather than
  a `bulk-discount` verdict) is a case change, tracked with F1's follow-up.
- No `teardown`: `new_user` state is ephemeral and `isolate` resets the cart before each case.

## Metadata the other layers read

- `covers = ["POST /checkout", "bulk-discount"]` — the route the scenario calls and the rule id it
  pins (DESIGN reports coverage over these; `POST /cart` is setup, not the surface under test).
- `contract_claim = {"rule": "bulk-discount", "rate": 0.10, "min_qty": 3}` — what DIAGNOSE checks against
  `BUSINESS_RULES` (`app.py:62-66`). Precisely (R-MECHANISM, `engine/diagnostics.py:89-94`): the `rule` id
  must resolve and **only `rate` is compared**; `min_qty` is carried in the claim but not compared. Claimed
  rate ≠ contract rate ⇒ `TEST_BUG`; rate agrees but the runtime violated the rule ⇒ `REAL_BUG`
  (`make diagnose-realbug` seeds exactly that). The verdict's `rule` label is the rule the *claim names*,
  not a fault localisation — see Design panel F3.

## Runtime expectations

Sub-second: four requests against the in-process mock.

**Shared state, named (Design panel F4).** The cart is one **server-global** object
(`sut/mock-shop/source/app.py:159` — `state = {"cart": []}`; no session scoping — `skills/SHOP.md`'s
"ephemeral per session" is inexact on this point). Two packs *mutate* it: SHOP-123 (adds, then reads
`GET /cart`) and this one (adds, then checks out — which clears it). The manifest's `isolate`
(`POST /cart/clear`) runs **before** a case and protects nothing against a *concurrent* case on the same
server. What makes `-n auto` safe today is the pytest bridge booting **one server per xdist worker**
(`tests/conftest.py:43-55`), with cases serial within a worker — not `isolate`. **Serial-only under any
shared-server or `remote` env** (`make serve`, or an env overriding `runtime.mode`): the two packs would
contend on one cart.

## Design panel

- ran: R-DESIGN 4 findings (2026-09-06, as a subagent carrying `agents/r-design.md` verbatim — the lens file was added mid-session, so its own agent type was not registered until the `.claude` wiring was regenerated; the re-run under the registered `r-design` type is recorded in the spec-005 validation report); R-MECHANISM (needs_mechanism) — 7/7 mechanism claims CITED against `sut/mock-shop/source/app.py`; freshness FRESH (in_process); every citation resolves (`engine.citation_gate`: 26 + 23, exit 0); needs_evidence false. Dispositions below are the GENERATOR's proposal for the human to ratify.
- F1 DEFERRED: valid gap — the ticket says "3 **or more**" and "counting quantities, not distinct products" (`sut/mock-shop/tickets/SHOP-456.md:37`, `:22-23`, `:43-44`) while the spec pins a single qty=3 line (`specs/SHOP-456-bulk-discount.md:14`), so a `>=`→`==` at `source/app.py:139` or `sum`→`max` at `:137` would still pass. Closing it means amending a human-approved spec (a third AC: a multi-line cart above the threshold, e.g. Widget×2 + Gizmo×2 → subtotal 28.0, discount 2.80) and extending the case — out of this retro-plan's scope (the spec-005 panel demonstrator); proposed as a SHOP-456 follow-up. Nothing is weakened.
- F2 APPLIED: the mapping rows now state what the case asserts — literal totals under the stated subtotal — instead of the AC's identity `total = subtotal − discount`, which the case never reads `order["subtotal"]` to check. Adding the `subtotal` + identity assertions (strictly more assertions) is a case change, folded into the F1 follow-up.
- F3 APPLIED: the second boundary's dependency on checkout clearing the cart is now named as an unchecked precondition in *REST mapping* and *Case shape*, with the attribution consequence spelled out (R-MECHANISM: the clear at `app.py:150` is synchronous, before the response at `:151`; a regression there would be routed to `REAL_BUG` labelled `bulk-discount` by `engine/diagnostics.py:80-119`, whose `rule` label is claim-derived, not fault-localised). The hardening (`expect.precondition` on the emptied cart and on the `POST /cart` status — a `PreconditionError` is a FAIL, not a SKIP) is a case change, folded into the F1 follow-up.
- F4 APPLIED: *Runtime expectations* rewritten — the cart is server-global (`app.py:159`), SHOP-123 and SHOP-456 both mutate it, parallel safety comes from one booted server per xdist worker (`tests/conftest.py:43-55`) and not from `isolate` (`engine/runner.py:64` runs it before a case; no concurrency fence), serial-only under a shared-server / `remote` env.
