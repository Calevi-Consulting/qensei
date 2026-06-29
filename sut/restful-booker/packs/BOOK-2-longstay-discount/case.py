"""BOOK-2 — the long-stay discount applies at the >=7-night threshold (new_user, REST).

Pins BOTH sides of the threshold (6 nights → no discount, 7 nights → 15% off), per the
availability/boundary learning. `contract_claim` lets the diagnostics layer tell a real
regression of this rule from a wrong test — the booker analog of mock-shop's SHOP-456.
This is the case the `make demo-booker` REAL_BUG/TEST_BUG demo drives off.
"""
from engine.case import RegressionCase


class LongStayDiscountApplies(RegressionCase):
    id = "BOOK-2"
    title = "long-stay discount applies at the >=7-night threshold"
    spec_ref = "sut/restful-booker/specs/BOOK-2-longstay-discount.md"
    persona = "new_user"
    tags = frozenset({"smoke"})
    severity = "critical"
    requires = ["rooms_available"]
    covers = ["POST /booking/", "longstay-discount"]
    contract_claim = {"rule": "longstay-discount", "rate": 0.15, "min_nights": 7}

    def _book(self, sut, checkin, checkout):
        return sut.post("/booking/", {
            "roomid": 1, "firstname": "Grace", "lastname": "Hopper", "depositpaid": False,
            "bookingdates": {"checkin": checkin, "checkout": checkout},
        })

    def run(self, sut, expect):
        # below threshold: 6 nights @ 100 = 600, no discount
        status, created = self._book(sut, "2025-06-01", "2025-06-07")
        expect.equal(status, 201, "booking (6 nights) status")
        b = (created or {}).get("booking", {})
        expect.approx(b.get("discount"), 0.0, "no discount below 7 nights (6)")
        expect.approx(b.get("totalprice"), 600.0, "totalprice below threshold")
        if (created or {}).get("bookingid"):
            sut.delete(f"/booking/{created['bookingid']}")  # free the dates before the next stay

        # at threshold: 7 nights @ 100 = 700, 15% off = 105 -> 595
        status, created = self._book(sut, "2025-07-01", "2025-07-08")
        expect.equal(status, 201, "booking (7 nights) status")
        b = (created or {}).get("booking", {})
        expect.approx(b.get("discount"), 105.0, "15% long-stay discount at threshold (7)")
        expect.approx(b.get("totalprice"), 595.0, "discounted total")
        self._bid = (created or {}).get("bookingid")

    def teardown(self, sut):
        bid = getattr(self, "_bid", None)
        if bid is not None:
            sut.delete(f"/booking/{bid}")
