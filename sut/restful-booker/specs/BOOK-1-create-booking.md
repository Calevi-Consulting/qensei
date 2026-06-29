# BOOK-1 — a booking is created and priced against a room

## Context
The core flow of the platform: an admin logs in, a guest books an existing room for a set
of dates, and the booking is retrievable. The price a guest sees is `roomPrice × nights`,
so a regression in that calculation is money and must be pinned.

## Requirements
- `POST /auth/login` with the documented admin credentials returns a session token.
- `POST /booking/` on an existing room returns 201 with a `bookingid` and the booking body.
- `totalprice = roomPrice × nights` (below the long-stay threshold, no discount).
- The created booking is retrievable via `GET /booking/{id}`.

## Acceptance Criteria
- [x] Admin login returns HTTP 200 and a non-empty token.
- [x] Booking a seeded room for 3 nights returns 201 with a booking id.
- [x] `totalprice == roomPrice × nights` (3 × 100 = 300) and `discount == 0`.
- [x] `GET /booking/{id}` returns the same booking.

## Integration-boundary AC
- [x] The case exercises the real `/auth/login` and `/booking/` endpoints of the SUT runtime
  (the in-process mock by default, or the live site under `QAF_ENV=live`), not a mock of them;
  the price is asserted on the live response.

## Persona coverage
- new_user (the booking is ephemeral and deleted on teardown).

## Risks & Assumptions
- Requires at least one room (`requires = [rooms_available]`); skips rather than fails on an
  empty environment. Rollback: none (the only durable write is none — the booking self-cleans).

## Status: COMPLETE
Automated by `sut/restful-booker/packs/BOOK-1-create-booking`.
