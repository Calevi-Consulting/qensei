"""SHOP-456 — bulk discount applies at the >=3 threshold (new_user, REST).

Pins BOTH sides of the threshold (qty=2 no discount, qty=3 discount), per the
off-by-one learning. `contract_claim` lets the diagnostics layer tell a real
regression of this rule from a wrong test.
"""
from engine.case import RegressionCase


class BulkDiscountApplies(RegressionCase):
    id = "SHOP-456"
    title = "bulk discount applies at the >=3 threshold"
    spec_ref = "core/specs/SHOP-456-bulk-discount.md"
    persona = "new_user"
    tags = frozenset({"smoke"})
    severity = "critical"
    covers = ["POST /checkout", "bulk-discount"]
    contract_claim = {"rule": "bulk-discount", "rate": 0.10, "min_qty": 3}

    def run(self, sut, expect):
        # below threshold: qty 2 -> no discount
        sut.post("/cart", {"product_id": 1, "qty": 2})  # 2 x 10 = 20
        status, order = sut.post("/checkout")
        expect.equal(status, 201, "checkout (qty2) status")
        expect.approx(order["discount"], 0.0, "no discount below threshold (qty2)")
        expect.approx(order["total"], 20.0, "total below threshold")

        # at threshold: qty 3 -> 10% off  (checkout cleared the cart, so re-add)
        sut.post("/cart", {"product_id": 1, "qty": 3})  # 3 x 10 = 30
        status, order = sut.post("/checkout")
        expect.equal(status, 201, "checkout (qty3) status")
        expect.approx(order["discount"], 3.0, "10% discount at threshold (qty3)")
        expect.approx(order["total"], 27.0, "discounted total")
