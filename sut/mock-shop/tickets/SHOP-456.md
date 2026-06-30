# SHOP-456 — Apply a 10% bulk discount at 3+ items

> Mock JIRA-style ticket for the qa-framework demo. The `mock-file` ticket provider
> (see [`ticket/contract.md`](../../../ticket/contract.md)) normalizes this file to
> `{id, title, description, acceptance_criteria[], status, links[]}`. It is the **entry** to
> `/spec-test` for the mock-shop domain and maps to
> [`sut/mock-shop/specs/SHOP-456-bulk-discount.md`](../specs/SHOP-456-bulk-discount.md).

| Field | Value |
|-------|-------|
| Key | SHOP-456 |
| Type | Story |
| Status | Done |
| Priority | High |
| Components | Checkout, Pricing |
| Labels | pricing, discount, regression-candidate |
| Reporter | product-owner@example.com |
| Verified by | QA (manual pass against the checkout flow) |

## Description

Checkout should reward larger baskets. When a shopper has **3 or more items** in the cart
(counting quantities, not distinct products), the order gets **10% off the subtotal**. Below
that threshold the shopper pays full price.

This is money and it has a threshold, which makes it a classic off-by-one site: a basket of
*exactly* 3 must already qualify, and a basket of 2 must not. Both sides of the boundary need
to be checked, not just "a big cart gets a discount". The order's `total` is always the
`subtotal` minus whatever `discount` was applied.

Manually validated by QA against the live checkout flow (qty 2 → full price, qty 3 → 10% off).
Now ready to be locked in as a permanent regression test.

## Acceptance Criteria

- [x] A cart whose total quantity is below 3 is charged full price — no discount.
- [x] A cart whose total quantity is 3 or more receives 10% off the subtotal.
- [x] The threshold is inclusive: exactly 3 items already qualifies (off-by-one guard).
- [x] The order `total` equals `subtotal` minus the applied `discount`.

## Links

- [type: spec] [SHOP-456 — bulk discount spec](../specs/SHOP-456-bulk-discount.md)
- [type: learnings] [Off-by-one threshold sites](../learnings/SHOP_LEARNINGS.md)
- [type: related] [SHOP-123 — cart total](../specs/SHOP-123-cart-total.md)
