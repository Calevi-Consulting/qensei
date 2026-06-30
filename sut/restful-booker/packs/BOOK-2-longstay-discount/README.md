# BOOK-2 — long-stay discount at the >=7-night threshold  · automated

REST regression (`new_user`): pins **both** sides of the threshold (6 nights → no discount,
7 nights → 15% off). Carries a `contract_claim` so the diagnostics lens can tell a real
regression of this rule from a wrong test — the booker counterpart to mock-shop's SHOP-456.

- Spec: [`sut/restful-booker/specs/BOOK-2-longstay-discount.md`](../../specs/BOOK-2-longstay-discount.md)
- Covers: `POST /booking/`, `longstay-discount`
- Tags: `smoke`
- Run: `python3 -m engine.run --sut sut/restful-booker`
- Diagnostics demo (REAL_BUG): `python3 -m engine.diagnose --sut sut/restful-booker --pack sut/restful-booker/packs/BOOK-2-longstay-discount --seed-bug`
