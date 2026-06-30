# BOOK-UI-1 — book a room through the web UI

## Context
The same core booking flow as BOOK-1, but verified **end-to-end through the front-end** rather than
the JSON API: a guest opens the booking page, picks a room, enters their details and dates, submits,
and sees a confirmation. This is the UI testing approach — a real browser driving the site's form —
the counterpart to the REST regression. It catches breakage the REST gate cannot (a broken form, a
mis-wired submit, a confirmation that never renders).

## Requirements
- The booking page lists the available rooms to choose from.
- Submitting the form with valid details creates the booking.
- The page shows a confirmation with the booking and its total (`roomPrice × nights`).

## Acceptance Criteria
- [x] The room selector is populated from the rooms endpoint.
- [x] Filling the form and submitting books seeded room 1 for 3 nights.
- [x] An on-screen confirmation appears showing the booking and the total `300`.

## Integration-boundary AC
- [x] The case drives a **real browser** (Playwright) against the site's live UI runtime — the
  in-process mock's `/ui` by default, or the live site's front-end — not a mock of the page.

## Persona coverage
- new_user (the booking is ephemeral; the UI bridge resets bookings before the case).

## Risks & Assumptions
- Requires at least one room (`requires = [rooms_available]`). UI tests are slower and more brittle
  than the REST gate, so they run in their own opt-in `ui` lane (`make test-ui`), not the default
  gate. Rollback: none (ephemeral booking).

## Status: COMPLETE
Automated by `sut/restful-booker/ui-packs/BOOK-UI-1-book-a-room` (Playwright). REST counterpart:
`sut/restful-booker/packs/BOOK-1-create-booking`.
