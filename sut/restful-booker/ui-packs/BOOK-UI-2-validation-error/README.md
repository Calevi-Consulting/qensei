# BOOK-UI-2 — booking validation error · automated (Playwright)

Browser-driven (`UICase`) regression: drives the booking form in a real browser, intentionally
leaves a required field blank, attempts submission, and verifies that the browser blocks the
request before a booking is created.

- Spec: `sut/restful-booker/specs/BOOK-UI-2-validation-error.md`
- Covers: `GET /ui`, `GET /room/`
- Tags: `ui`
- Run (headless): `make test-ui`
- Watch it live (headed, slow): `make ui-watch`
- Single run: `poetry run pytest tests/test_ui.py -m ui`