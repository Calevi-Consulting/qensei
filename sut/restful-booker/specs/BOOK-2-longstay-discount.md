# BOOK-2 — long-stay discount applies at the >=7-night threshold

## Context
A stay of 7 nights or more earns a 15% discount on the room subtotal. It is money, and it
has a threshold — the classic off-by-one site (see `BOOKER_LEARNINGS`). This is the booker
site's diagnosable business rule: its `contract_claim` is what lets the diagnostics lens tell
a real regression apart from a wrong test.

> The long-stay discount is an illustrative rule this mock adds on top of the real platform
> surface, to exercise the REAL_BUG/TEST_BUG seam (`BUSINESS_RULES['longstay-discount']`).

## Requirements
- A stay shorter than 7 nights gets no discount.
- A stay of 7+ nights gets 15% off the room subtotal (`roomPrice × nights`).
- `totalprice = subtotal − discount`.

## Acceptance Criteria
- [x] 6 nights → `discount == 0`, `totalprice == 600`.
- [x] 7 nights → `discount == 105` (15% of 700), `totalprice == 595`.

## Integration-boundary AC
- [x] The case exercises the real `/booking/` endpoint of the SUT runtime (not a mock of it);
  the discount is asserted on the live response. The `--seed-bug` runtime drops the discount to
  reproduce a regression the diagnostics lens classifies REAL_BUG.

## Persona coverage
- new_user (both bookings are ephemeral and removed on teardown).

## Risks & Assumptions
- Requires at least one room (`requires = [rooms_available]`). The two stays use distinct,
  non-overlapping date ranges so the availability rule never interferes. Rollback: none.

## Status: COMPLETE
Automated by `sut/restful-booker/packs/BOOK-2-longstay-discount`. The diagnostics demo seeds a
regression of this rule (`--seed-bug`) to show REAL_BUG detection.
