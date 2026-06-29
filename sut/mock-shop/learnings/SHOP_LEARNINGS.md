# SHOP_LEARNINGS — accumulated patterns (mock-shop)

Append-only, framework-authored. Each entry encodes a REUSABLE pattern discovered
while designing, running, or diagnosing cases against this backend — not a one-off
run record. (Mirrors the durable-vs-ephemeral learnings discipline.)

- **The bulk-discount threshold is the off-by-one magnet.** Failures clustered at qty=2 vs
  qty=3. A regression for `bulk-discount` should pin *both* sides of the boundary (qty=2 → no
  discount, qty=3 → discount), not just the happy path. Covered by `SHOP-456`.
- **Diagnose a discount miss against the source, not the test.** A checkout returning full
  price can be either a wrong test (asserted the wrong rate) or a real regression (rate dropped
  to 0). The `contract_claim` on the case + `BUSINESS_RULES` in the source disambiguate — see
  `engine/diagnostics.py`. Recorded after the REAL_BUG vs TEST_BUG demo.
