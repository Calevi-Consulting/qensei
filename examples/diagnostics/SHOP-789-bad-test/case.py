"""SHOP-789 — an INTENTIONALLY WRONG test, used only to demo TEST_BUG triage.

It asserts a 20% bulk discount. The backend contract (source BUSINESS_RULES) is 10%,
so this fails against a CORRECT backend. The diagnostics layer reads the source and
classifies it TEST_BUG (fix the test; do not weaken the spec) — NOT a platform bug.

This pack lives outside packs/ on purpose, so the real regression gate stays green.
"""
from engine.case import RegressionCase


class WrongDiscountRateTest(RegressionCase):
    id = "SHOP-789"
    title = "(intentionally wrong) asserts a 20% bulk discount"
    spec_ref = "examples/diagnostics/SHOP-789-bad-test/README.md"
    persona = "new_user"
    covers = ["POST /checkout", "bulk-discount"]
    contract_claim = {"rule": "bulk-discount", "rate": 0.20, "min_qty": 3}

    def run(self, sut, expect):
        sut.post("/cart", {"product_id": 1, "qty": 3})  # 30.0
        status, order = sut.post("/checkout")
        expect.equal(status, 201, "checkout status")
        expect.approx(order["discount"], 6.0, "expected 20% discount")  # WRONG: contract is 10%
        expect.approx(order["total"], 24.0, "expected discounted total")
