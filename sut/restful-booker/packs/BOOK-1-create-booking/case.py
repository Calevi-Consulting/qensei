"""BOOK-1 — a booking is created and priced against a seeded room (new_user, REST).

The happy path of the platform's core flow: log in, create a booking on an existing room,
and read it back. Pins the price contract (totalprice = roomPrice x nights) below the
long-stay threshold so this case stays a pure create/read check (the threshold itself is
BOOK-2's job).
"""
from engine.case import RegressionCase


class CreateBookingPricesTheStay(RegressionCase):
    id = "BOOK-1"
    title = "a booking is created and priced against a room"
    spec_ref = "sut/restful-booker/specs/BOOK-1-create-booking.md"
    persona = "new_user"
    tags = frozenset({"smoke"})
    severity = "high"
    requires = ["rooms_available"]
    covers = ["POST /auth/login", "POST /booking/", "GET /booking/{id}"]

    def run(self, sut, expect):
        # the platform's documented admin login returns a session token
        status, auth = sut.post("/auth/login", {"username": "admin", "password": "password"})
        expect.equal(status, 200, "admin login status")
        expect.is_not_none((auth or {}).get("token"), "login returns a token")

        # book seeded room 1 (@100/night) for 3 nights -> 201, priced 300, no long-stay discount
        booking = {
            "roomid": 1, "firstname": "Ada", "lastname": "Lovelace", "depositpaid": True,
            "email": "ada@example.com", "phone": "01234567890",
            "bookingdates": {"checkin": "2025-05-01", "checkout": "2025-05-04"},
        }
        status, created = sut.post("/booking/", booking)
        expect.equal(status, 201, "create booking status")
        bid = (created or {}).get("bookingid")
        expect.is_not_none(bid, "booking id returned")
        body = (created or {}).get("booking", {})
        expect.equal(body.get("roomid"), 1, "booking is for the requested room")
        expect.approx(body.get("totalprice"), 300.0, "totalprice = roomPrice x nights (3 x 100)")
        expect.approx(body.get("discount"), 0.0, "no long-stay discount below 7 nights")

        # the created booking is retrievable
        status, fetched = sut.get(f"/booking/{bid}")
        expect.equal(status, 200, "GET booking status")
        expect.equal((fetched or {}).get("bookingid"), bid, "GET returns the same booking")
        self._bid = bid

    def teardown(self, sut):
        bid = getattr(self, "_bid", None)
        if bid is not None:  # new_user: remove what we created (best-effort)
            sut.delete(f"/booking/{bid}")
