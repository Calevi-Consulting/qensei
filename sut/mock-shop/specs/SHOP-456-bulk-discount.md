# SHOP-456 — bulk discount applies at the >=3 threshold

## Context
Checkout applies a 10% discount once the cart holds ≥ 3 items total. It is money,
and it has a threshold — the classic off-by-one site (see `SHOP_LEARNINGS`).

## Requirements
- A cart with total qty < 3 gets no discount.
- A cart with total qty ≥ 3 gets 10% off the subtotal.
- Order `total` = `subtotal` − `discount`.

## Acceptance Criteria
- [x] qty=2 → discount 0.0, total = subtotal.
- [x] qty=3 → discount = 10% of subtotal, total = subtotal − discount.

## Integration-boundary AC
- [x] The case exercises the real `/checkout` endpoint of the SUT (not a mock of it);
  the discount is asserted on the live response.

## Persona coverage
- new_user.

## Risks & Assumptions
- Checkout is destructive (clears the cart) — the case re-adds between the two
  boundary checks. Rollback: ephemeral state, nothing persisted.

## Status: COMPLETE
Automated by `sut/mock-shop/packs/SHOP-456-discount`. The diagnostics demo seeds a regression of
this rule (`--seed-bug`) to show REAL_BUG detection.
