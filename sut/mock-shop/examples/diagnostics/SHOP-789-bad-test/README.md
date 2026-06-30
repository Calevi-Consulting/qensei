# SHOP-789 — intentionally wrong test (TEST_BUG demo)

Not a real regression — a teaching example. It asserts a **20%** bulk discount; the backend
contract (`BUSINESS_RULES['bulk-discount']` in the source) is **10%**, so it fails against a
*correct* backend.

Running it through diagnostics shows the lens reading the source contract and classifying the
failure **TEST_BUG** (fix the test's expectation; do not weaken the spec) — the counterpart to
the REAL_BUG verdict that `SHOP-456 --seed-bug` produces.

It lives outside the SUT's `packs/` dir on purpose, so the real regression gate (`make test`) stays green.

```bash
python3 -m engine.diagnose --sut sut/mock-shop --pack sut/mock-shop/examples/diagnostics/SHOP-789-bad-test
```
