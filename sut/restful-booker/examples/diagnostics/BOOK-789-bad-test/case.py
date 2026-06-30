"""BOOK-789 — an INTENTIONALLY WRONG test, used only to demo TEST_BUG triage.

It asserts a 25% long-stay discount. The backend contract (source BUSINESS_RULES) is 15%,
so this fails against a CORRECT backend. The diagnostics layer reads the source and
classifies it TEST_BUG (fix the test; do not weaken the spec) — NOT a platform bug. The
booker counterpart to mock-shop's SHOP-789.

This pack lives outside the SUT's packs/ dir on purpose, so the real regression gate stays green.
"""
from engine.case import RegressionCase


class WrongLongStayRateTest(RegressionCase):
    id = "BOOK-789"
    title = "(intentionally wrong) asserts a 25% long-stay discount"
    spec_ref = "sut/restful-booker/examples/diagnostics/BOOK-789-bad-test/README.md"
    persona = "new_user"
    covers = ["POST /booking/", "longstay-discount"]
    contract_claim = {"rule": "longstay-discount", "rate": 0.25, "min_nights": 7}

    def run(self, sut, expect):
        # 7 nights @ 100 = 700; the contract gives 15% off (595). This test wrongly expects 25%.
        status, created = sut.post("/booking/", {
            "roomid": 1, "firstname": "Grace", "lastname": "Hopper", "depositpaid": False,
            "bookingdates": {"checkin": "2025-08-01", "checkout": "2025-08-08"},
        })
        expect.equal(status, 201, "create booking status")
        b = (created or {}).get("booking", {})
        expect.approx(b.get("discount"), 175.0, "expected 25% discount")  # WRONG: contract is 15%
        expect.approx(b.get("totalprice"), 525.0, "expected discounted total")
