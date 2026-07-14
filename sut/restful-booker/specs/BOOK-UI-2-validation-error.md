# BOOK-UI-2 — booking validation error

## Context
Verifies the booking form's client-side validation by attempting to submit an incomplete booking.
Instead of exercising the successful booking flow, this case leaves one required field blank and
confirms that the browser blocks submission before any request reaches the backend. This complements
the successful UI booking scenario by covering the validation/error path.

## Requirements
- The booking page lists the available rooms.
- The booking form enforces the required fields.
- An incomplete submission is prevented by the browser.

## Acceptance Criteria
- [x] The room selector is populated from the rooms endpoint.
- [x] The booking is attempted with the required **Last name** field left blank.
- [x] No booking confirmation is shown.
- [x] No backend error message is shown because the request is never submitted.

## Integration-boundary AC
- [x] The case drives a **real browser** (Playwright) against the site's live UI runtime — the
  in-process mock's `/ui` by default, or the live site's front-end — relying on the browser's
  native HTML form validation.

## Persona coverage
- new_user (no booking is created because submission is blocked by client-side validation).

## Risks & Assumptions
- Requires at least one room (`requires = ["rooms_available"]`).
- Assumes the booking form continues using HTML5 `required` validation for mandatory fields.
- Rollback: none (no booking is created).

## Status: COMPLETE
Automated by `sut/restful-booker/ui-packs/BOOK-UI-2-validation-error` (Playwright). Complements
`BOOK-UI-1-book-a-room` by covering the validation/error path.