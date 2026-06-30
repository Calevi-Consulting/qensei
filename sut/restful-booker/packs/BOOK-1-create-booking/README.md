# BOOK-1 — create a booking, priced against a room  · automated

REST regression (`new_user`): logs in, creates a booking on seeded room 1, asserts the price
contract (`totalprice = roomPrice × nights`) below the long-stay threshold, and reads the
booking back. Self-cleans (deletes the booking it created) so it leaves the site as found.

- Spec: [`sut/restful-booker/specs/BOOK-1-create-booking.md`](../../specs/BOOK-1-create-booking.md)
- Covers: `POST /auth/login`, `POST /booking/`, `GET /booking/{id}`
- Tags: `smoke`
- Run: `python3 -m engine.run --sut sut/restful-booker`
