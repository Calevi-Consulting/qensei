"""BOOK-UI-1 — book a room through the web UI (new_user, Playwright UI).

The UI counterpart to the REST packs: instead of calling POST /booking/ directly, it drives the
site's booking FORM in a real browser (fill fields, pick a room, submit) and asserts the on-screen
confirmation — genuine end-to-end coverage through the front-end. Run headed (`make ui-watch`) to
watch the verification live. Against the mock this is deterministic and offline; pointed at the
live site's UI it exercises the real front-end.
"""
from engine.ui import UICase


class BookingValidationError(UICase):
    id = "BOOK-UI-2"
    title = "booking validation error"
    spec_ref = "sut/restful-booker/specs/BOOK-UI-2-validation-error.md"
    persona = "new_user"
    tags = frozenset({"ui"})
    severity = "high"
    requires = ["rooms_available"]
    covers = ["GET /ui", "GET /room/", "POST /booking/"]

    def run(self, page, base_url, expect):
        page.goto(base_url)

        # the room <select> is populated from GET /room/ on load — wait for an option to be ATTACHED
        # (an <option> is never "visible" to Playwright, so the default visible-wait would time out)
        page.wait_for_selector("#room option", state="attached")
        page.fill("#firstname", "Ada")
        page.fill("#lastname", "Lovelace")
        page.select_option("#room", "1")          # seeded room 1 @ 100/night
        page.fill("#checkin", "2025-10-01")
        page.fill("#checkout", "2025-10-04")       # 3 nights -> total 300, no long-stay discount
        page.click("#book-btn")

        page.wait_for_selector("#confirmation:not([hidden])")
        confirmation = page.text_content("#confirmation") or ""
        expect.that("confirmed" in confirmation.lower(), f"booking confirmation shown: {confirmation!r}")
        expect.that("300" in confirmation, f"total (3 x 100) shown in confirmation: {confirmation!r}")
