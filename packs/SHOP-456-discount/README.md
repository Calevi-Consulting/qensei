# SHOP-456 — bulk discount at the >=3 threshold  · automated

REST regression (`new_user`): pins **both** sides of the threshold (qty=2 → no discount,
qty=3 → 10% off), per the off-by-one learning. Carries a `contract_claim` so the diagnostics
lens can tell a real regression of this rule from a wrong test.

- Spec: [`core/specs/SHOP-456-bulk-discount.md`](../../core/specs/SHOP-456-bulk-discount.md)
- Covers: `POST /checkout`, `bulk-discount`
- Run: `python3 -m engine.run --sut sut/mock-shop`
- Diagnostics demo (REAL_BUG): `python3 -m engine.diagnose --sut sut/mock-shop --pack packs/SHOP-456-discount --seed-bug`
