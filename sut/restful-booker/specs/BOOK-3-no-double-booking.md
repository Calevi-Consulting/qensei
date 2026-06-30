# BOOK-3 — a room cannot be double-booked

## Context
The platform's core availability promise: a room can hold only one booking per date range.
Bookings are half-open `[checkin, checkout)`, so a stay that starts on a prior stay's checkout
date does not overlap and must be accepted — the off-by-one boundary of this domain. This is
the REAL restful-booker-platform rule (`BUSINESS_RULES['no-double-booking']`), not illustrative.

## Requirements
- Booking overlapping dates on the same room is rejected with HTTP 409.
- A stay that touches (starts on the prior checkout) is accepted.
- `checkin >= checkout` is rejected with HTTP 409.

## Acceptance Criteria
- [x] A first booking on free dates is accepted (201).
- [x] An overlapping booking on the same room is rejected (409).
- [x] A touching booking (checkin == prior checkout) is accepted (201).
- [x] `checkin == checkout` is rejected (409).

## Integration-boundary AC
- [x] The case exercises the real `/booking/` endpoint of the SUT runtime (not a mock of it);
  the 409 conflict is asserted on the live response, both for overlap and for invalid dates.

## Persona coverage
- new_user (the accepted bookings are removed on teardown).

## Risks & Assumptions
- Requires at least one room (`requires = [rooms_available]`). The runner's `isolate`
  (`/booking/reset`) clears bookings before the case, so prior cases cannot pollute the dates.
  Rollback: none (ephemeral bookings, self-cleaned).

## Status: COMPLETE
Automated by `sut/restful-booker/packs/BOOK-3-no-double-booking`.
