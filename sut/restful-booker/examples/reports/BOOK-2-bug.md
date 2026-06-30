# Demo bug report — the long-stay-discount regression (restful-booker)

A filled `/report-bug` output for the REAL_BUG the diagnostics demo finds (`make demo-booker`):
the seeded `--seed-bug` booker mock drops the long-stay discount. Shows the six-section format
end-to-end on the booker domain; on a real tenant the fields would render as ADF and resolve
through `jira.fields.json`.

---

**Summary**
`restful-booker - Booking - Revenue loss: long-stay discount not applied at the >=7-night threshold`

**Description**
```gherkin
Given a 7-night booking on room 1 (subtotal 700.00)
When the booking is created
Then it should apply the 15% long-stay discount (discount 105.00, total 595.00)
```
**Impact:** every qualifying booking is overcharged by the discount amount — a guest-facing
billing error and a contract (BUSINESS_RULES `longstay-discount`) violation.
**Reproduction across environments:** reproduces on the booker mock started with `--seed-bug`;
does not reproduce on the healthy backend.
**Related:** spec `sut/restful-booker/specs/BOOK-2-longstay-discount.md`; regression
`sut/restful-booker/packs/BOOK-2-longstay-discount`.

{expand:Affected Endpoint Details}
Method: POST
URL: /booking/
Response Code: 201
Response Body:
{code}
{ "booking": { "subtotal": 700, "discount": 0, "totalprice": 700 } }
{code}
Expected: discount 105.0, totalprice 595.0
{expand}

**Steps to Reproduce**
```
0. Preconditions: booker running with the seeded regression (engine boots it with buggy=True)
1. POST /booking/  { "roomid": 1, "bookingdates": { "checkin": "2025-07-01", "checkout": "2025-07-08" }, ... }
2. Read booking.totalprice
```

**Actual Behavior**
`/booking/` returns `discount: 0`, `totalprice: 700` — no discount applied.

**Expected Behavior**
Per `BUSINESS_RULES['longstay-discount']` (rate 0.15, min_nights 7): `discount: 105.0`, `totalprice: 595.0`.

**Environment**
```
Environment: restful-booker @ local (in-process mock)
Backend source: sut/restful-booker/source/app.py
```

---

**Classification** — Component: Back End · Priority: High · Severity: Major · Is regression: **Yes**
(the healthy backend honours the rule) · Issue type: Bug.

**Diagnostic provenance:** classified **REAL_BUG** by `engine/diagnostics.py` — the case's
`contract_claim` (rate 0.15) matches the backend contract, but the running system violated it. The
test stays red; this bug is filed. (Contrast: `make diagnose-testbug SUT=sut/restful-booker`, where a
wrong test asserting 25% is classified TEST_BUG and no bug is filed.)
