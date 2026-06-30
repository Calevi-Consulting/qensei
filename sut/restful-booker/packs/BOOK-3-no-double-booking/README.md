# BOOK-3 — a room cannot be double-booked  · automated

REST regression (`new_user`): pins the platform's availability promise — overlapping stays on
a room are rejected with **409**, a stay that *touches* (starts on the prior checkout) is
**accepted** (half-open dates, the off-by-one boundary), and `checkin == checkout` is rejected.
This is the REAL restful-booker-platform behaviour, not an illustrative rule.

- Spec: [`sut/restful-booker/specs/BOOK-3-no-double-booking.md`](../../specs/BOOK-3-no-double-booking.md)
- Covers: `POST /booking/`, `no-double-booking`
- Tags: `smoke`
- Run: `python3 -m engine.run --sut sut/restful-booker`
