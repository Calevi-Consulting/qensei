# BOOK-2 — Apply a 15% long-stay discount at 7+ nights

> Mock JIRA-style ticket for the restful-booker site demo. The `mock-file` ticket provider
> (see [`ticket/contract.md`](../../../ticket/contract.md)) normalizes this file to
> `{id, title, description, acceptance_criteria[], status, links[], comments[]}`. It is the **entry** to
> `/automate` for the booker domain and maps to
> [`sut/restful-booker/specs/BOOK-2-longstay-discount.md`](../specs/BOOK-2-longstay-discount.md).

| Field | Value |
|-------|-------|
| Key | BOOK-2 |
| Type | Story |
| Status | Done |
| Priority | High |
| Components | Booking, Pricing |
| Labels | pricing, discount, regression-candidate |
| Reporter | product-owner@example.com |
| Verified by | QA (manual pass against the booking flow) |

## Description

Reward longer stays. When a guest books **7 nights or more** on a room, the booking gets
**15% off** the room subtotal (`roomPrice × nights`). Below that threshold the guest pays the
full subtotal.

This is money and it has a threshold, which makes it a classic off-by-one site: a stay of
*exactly* 7 nights must already qualify, and a stay of 6 must not. Both sides of the boundary
need to be checked, not just "a long stay gets a discount". The booking's `totalprice` is
always the `subtotal` minus whatever `discount` was applied.

Manually validated by QA against the booking flow (6 nights → full price, 7 nights → 15% off).
Now ready to be locked in as a permanent regression test.

## Acceptance Criteria

- [x] A stay shorter than 7 nights is charged the full subtotal — no discount.
- [x] A stay of 7+ nights receives 15% off the subtotal.
- [x] The threshold is inclusive: exactly 7 nights already qualifies (off-by-one guard).
- [x] The booking `totalprice` equals `subtotal` minus the applied `discount`.

## Links

- [type: spec] [BOOK-2 — long-stay discount spec](../specs/BOOK-2-longstay-discount.md)
- [type: learnings] [Off-by-one boundary sites](../learnings/BOOKER_LEARNINGS.md)
- [type: related] [BOOK-3 — no double booking](../specs/BOOK-3-no-double-booking.md)
