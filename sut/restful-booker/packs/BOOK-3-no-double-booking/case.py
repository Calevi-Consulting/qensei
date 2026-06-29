"""BOOK-3 — a room cannot be double-booked; touching stays are allowed (new_user, REST).

The platform's core availability promise, and the off-by-one magnet of this domain: bookings
are half-open `[checkin, checkout)`, so a stay that STARTS on a prior stay's checkout date does
NOT overlap and must be accepted, while a genuinely overlapping stay is rejected with 409.
Pins both sides of the boundary plus the checkin>=checkout guard. This is the REAL platform
rule (see BUSINESS_RULES['no-double-booking']), reproduced faithfully.
"""
from engine.case import RegressionCase


class NoDoubleBooking(RegressionCase):
    id = "BOOK-3"
    title = "overlapping bookings are rejected (409); touching stays allowed"
    spec_ref = "sut/restful-booker/specs/BOOK-3-no-double-booking.md"
    persona = "new_user"
    tags = frozenset({"smoke"})
    severity = "high"
    requires = ["rooms_available"]
    covers = ["POST /booking/", "no-double-booking"]

    def _book(self, sut, checkin, checkout):
        status, created = sut.post("/booking/", {
            "roomid": 1, "firstname": "Alan", "lastname": "Turing", "depositpaid": False,
            "bookingdates": {"checkin": checkin, "checkout": checkout},
        })
        if status == 201 and (created or {}).get("bookingid"):
            self._created.append(created["bookingid"])
        return status

    def run(self, sut, expect):
        self._created = []

        # a first stay is accepted
        expect.equal(self._book(sut, "2025-09-10", "2025-09-15"), 201, "first booking accepted")
        # overlapping dates on the same room -> 409
        expect.equal(self._book(sut, "2025-09-12", "2025-09-18"), 409, "overlapping booking rejected (409)")
        # a stay that STARTS on the prior checkout date does not overlap -> accepted
        expect.equal(self._book(sut, "2025-09-15", "2025-09-20"), 201, "touching booking accepted (half-open)")
        # checkin >= checkout is itself invalid -> 409
        expect.equal(self._book(sut, "2025-09-25", "2025-09-25"), 409, "checkin == checkout rejected (409)")

    def teardown(self, sut):
        for bid in getattr(self, "_created", []):  # new_user: remove what we created
            sut.delete(f"/booking/{bid}")
