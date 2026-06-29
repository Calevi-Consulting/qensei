# SHOP — domain knowledge (mock-shop)

Manual-QA context an agent uses to design and validate cases for this backend. The
generic analog of a domain skill file: what the product does, where the contracts
live, and the gotchas worth knowing before writing a case.

## Surface
- **Products** are read-only (`GET /products`, `GET /products/{id}`); ids 1–3 exist, others 404.
- **Cart** is server-side and ephemeral per session: `POST /cart {product_id, qty}` appends,
  `GET /cart` reads, `POST /cart/clear` empties. `total` = Σ price·qty.
- **Checkout** (`POST /checkout`) turns the cart into an order and **clears it**, returning
  `{items, subtotal, discount, total}`.

## Contracts that matter for regression
- **bulk-discount**: a cart with **≥ 3 items total** gets **10% off** the subtotal at checkout.
  This is the highest-value behaviour to protect — it is money, and it has a threshold (an
  off-by-one magnet). The authoritative values live in the source as `DISCOUNT_RATE` /
  `DISCOUNT_MIN_QTY` and in `BUSINESS_RULES['bulk-discount']`.

## Gotchas
- Checkout is **destructive** (clears the cart) — a case that needs the cart afterward must
  re-add. Cases should start from `POST /cart/clear` (the runner does this for isolation).
- The threshold counts **total quantity**, not distinct line items — qty=3 of one product
  triggers the discount; three lines of qty=1 also do.
