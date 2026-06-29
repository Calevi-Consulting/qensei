# Demo bug report — the bulk-discount regression (mock-shop)

A filled `/report-bug` output for the REAL_BUG the diagnostics demo finds (`make diagnose-realbug`):
the seeded `--seed-bug` mock-shop drops the bulk discount. Shows the six-section format end-to-end on
the mock domain; on a real tenant the fields would render as ADF and resolve through
`jira.fields.json`.

---

**Summary**
`mock-shop - Checkout - Revenue loss: bulk discount not applied at the >=3 threshold`

**Description**
```gherkin
Given a cart with 3 units of Widget (subtotal 30.00)
When the cart is checked out
Then the order should apply the 10% bulk discount (discount 3.00, total 27.00)
```
**Impact:** every qualifying order is overcharged by the discount amount — a customer-facing billing
error and a contract (BUSINESS_RULES `bulk-discount`) violation.
**Reproduction across environments:** reproduces on mock-shop started with `--seed-bug`; does not
reproduce on the healthy backend.
**Related:** spec `core/specs/SHOP-456-bulk-discount.md`; regression `packs/SHOP-456-discount`.

{expand:Affected Endpoint Details}
Method: POST
URL: /checkout
Response Code: 201
Response Body:
{code}
{ "subtotal": 30.0, "discount": 0.0, "total": 30.0 }
{code}
Expected: discount 3.0, total 27.0
{expand}

**Steps to Reproduce**
```
0. Preconditions: mock-shop running with the seeded regression (engine boots it with buggy=True)
1. POST /cart  { "product_id": 1, "qty": 3 }
2. POST /checkout
```

**Actual Behavior**
`/checkout` returns `discount: 0.0`, `total: 30.0` — no discount applied.

**Expected Behavior**
Per `BUSINESS_RULES['bulk-discount']` (rate 0.10, min_qty 3): `discount: 3.0`, `total: 27.0`.

**Environment**
```
Environment: mock-shop @ local (in-process)
Backend source: sut/mock-shop/source/app.py
```

---

**Classification** — Component: Back End · Priority: High · Severity: Major · Is regression: **Yes**
(the healthy backend honours the rule) · Issue type: Bug.

**Diagnostic provenance:** classified **REAL_BUG** by `engine/diagnostics.py` — the case's
`contract_claim` (rate 0.10) matches the backend contract, but the running system violated it. The
test stays red; this bug is filed. (Contrast: `make diagnose-testbug`, where a wrong test asserting
20% is classified TEST_BUG and no bug is filed.)
