# SHOP-123 — cart total reflects added items

## Context
The cart total is the number the user trusts before paying. A regression that
miscomputes it is high-impact and silent.

## Requirements
- Adding products updates `total` to Σ(price × qty).
- The total is identical whether read from the POST response or `GET /cart`.

## Acceptance Criteria
- [x] Adding Widget×2 (10.0) + Gadget×1 (25.0) yields cart total 45.0.
- [x] `GET /cart` returns the same total as the last POST response.

## Persona coverage
- new_user (ephemeral cart; isolated per run).

## Risks & Assumptions
None beyond standard — read/compute path only, no destructive ops.

## Status: COMPLETE
Automated by `packs/SHOP-123-cart-total`.
