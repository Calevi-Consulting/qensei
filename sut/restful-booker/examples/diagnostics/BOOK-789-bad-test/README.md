# BOOK-789 — intentionally wrong test (TEST_BUG demo)

Not a real regression — a teaching example. It asserts a **25%** long-stay discount; the
backend contract (`BUSINESS_RULES['longstay-discount']` in the source) is **15%**, so it fails
against a *correct* backend.

Running it through diagnostics shows the lens reading the source contract and classifying the
failure **TEST_BUG** (fix the test's expectation; do not weaken the spec) — the counterpart to
the REAL_BUG verdict that `BOOK-2 --seed-bug` produces. The booker analog of SHOP-789.

It lives outside the SUT's `packs/` dir on purpose, so the real regression gate (`make test`) stays green.

```bash
python3 -m engine.diagnose --sut sut/restful-booker --pack sut/restful-booker/examples/diagnostics/BOOK-789-bad-test
```
