"""SHOP-123 — cart total reflects added items (new_user, REST)."""
from engine.case import RegressionCase


class CartTotalReflectsAddedItems(RegressionCase):
    id = "SHOP-123"
    title = "cart total reflects added items"
    spec_ref = "core/specs/SHOP-123-cart-total.md"
    persona = "new_user"
    tags = frozenset({"smoke"})
    severity = "high"
    covers = ["POST /cart", "GET /cart"]

    def run(self, sut, expect):
        status, _ = sut.post("/cart", {"product_id": 1, "qty": 2})  # 2 x 10.0
        expect.equal(status, 200, "add Widget x2 status")
        status, cart = sut.post("/cart", {"product_id": 2, "qty": 1})  # 1 x 25.0
        expect.equal(status, 200, "add Gadget x1 status")
        expect.approx(cart["total"], 45.0, "cart total after POSTs")

        status, cart = sut.get("/cart")
        expect.equal(status, 200, "GET /cart status")
        expect.approx(cart["total"], 45.0, "cart total via GET")
