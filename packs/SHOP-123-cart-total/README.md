# SHOP-123 — cart total reflects added items  · automated

REST regression (`new_user`, ephemeral): adds Widget×2 + Gadget×1 and asserts the cart
`total` is 45.0 via both the POST response and `GET /cart`. Protects the number the user
trusts before paying.

- Spec: [`core/specs/SHOP-123-cart-total.md`](../../core/specs/SHOP-123-cart-total.md)
- Covers: `POST /cart`, `GET /cart`
- Run: `python3 -m engine.run --sut sut/mock-shop`
