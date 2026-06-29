# BOOK-UI-1 — book a room through the web UI  · automated (Playwright)

Browser-driven (`UICase`) regression: drives the booking **form** in a real browser — loads the
rooms, fills the guest + dates, picks room 1, submits, and asserts the on-screen confirmation shows
the booking and the total (3 nights × 100 = 300). The UI counterpart to the REST `BOOK-1` pack.

- Spec: [`sut/restful-booker/specs/BOOK-UI-1-book-a-room.md`](../../specs/BOOK-UI-1-book-a-room.md)
- Covers: `GET /ui`, `GET /room/`, `POST /booking/`
- Tags: `ui`
- Run (headless): `make test-ui`
- Watch it live (headed, slow): `make ui-watch`
- Single run: `poetry run pytest tests/test_ui.py -m ui`
