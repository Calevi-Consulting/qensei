"""BOOK-UI-2 — validation blocks an incomplete booking through the web UI (new_user, Playwright UI).

The UI counterpart to the REST validation path: instead of submitting a valid booking, it attempts
to submit the booking form with a required field missing and verifies that the browser blocks the
submission before any request reaches the backend.
"""
from engine.ui import UICase


class ValidationBlocksIncompleteBooking(UICase):
    id = "BOOK-UI-2"
    title = "booking validation error"
    spec_ref = "sut/restful-booker/specs/BOOK-UI-2-validation-error.md"
    persona = "new_user"
    tags = frozenset({"ui"})
    severity = "high"
    requires = ["rooms_available"]
    covers = ["GET /ui", "GET /room/"]

    def run(self, page, base_url, expect):
        page.goto(base_url)

        page.wait_for_selector("#room option", state="attached")

        page.fill("#firstname", "Ada")
        # leave lastname blank intentionally

        page.select_option("#room", "1")

        page.fill("#checkin", "2025-10-01")
        page.fill("#checkout", "2025-10-04")

        page.click("#book-btn")

        form_valid = page.eval_on_selector(
            "#booking-form",
            "f => f.checkValidity()",
        )

        expect.that(
            form_valid is False,
            "form should be invalid (lastname required, left blank)",
        )

        expect.that(
            page.is_hidden("#confirmation"),
            "no booking confirmation shown",
        )

        expect.that(
            page.is_hidden("#error"),
            "no backend error shown (request never submitted)",
        )
