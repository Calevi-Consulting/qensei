# BOOKER_LEARNINGS — accumulated patterns (restful-booker)

Append-only, framework-authored. Each entry encodes a REUSABLE pattern discovered while
designing, running, or diagnosing cases against this backend — not a one-off run record.
(Same discipline as `sut/mock-shop/learnings/SHOP_LEARNINGS.md`; the second site proves the
pattern is product-neutral.)

- **Availability is the off-by-one magnet here, like the discount threshold was on mock-shop.**
  A booking `[checkin, checkout)` is half-open: a new stay that *starts on* a prior stay's
  checkout date does NOT overlap and must be accepted, while one that starts a day earlier must
  be rejected with 409. A `no-double-booking` regression should pin *both* sides of the boundary
  (touching → allowed, overlapping → 409), not just "a clashing booking fails". Covered by `BOOK-3`.
- **Diagnose a price/discount miss against the source, not the test.** A booking that returns the
  un-discounted `totalprice` can be a wrong test (asserted the wrong rate) or a real regression
  (the long-stay discount stopped applying). The case's `contract_claim` + `BUSINESS_RULES` in the
  source disambiguate — identical seam to mock-shop's bulk-discount. Recorded after the booker
  REAL_BUG vs TEST_BUG demo (`make demo-booker`).
- **One plugin, two runtimes.** The booker boots an in-process mock by default and connects to the
  real public site under `QAF_ENV=live` (the env overrides `runtime.mode` to `remote`). Keep packs
  runtime-agnostic — assert behavioural contracts (`totalprice`, the 409), never an in-process
  detail — so the SAME pack validates the mock locally and the live site on demand.
- **Rooms durable, bookings ephemeral.** New_user booking cases must not depend on rooms they did
  not create; book against a seeded room (roomid 1) and let the `/booking/reset` isolate seam clear
  bookings between cases. Only the `existing_data` durable-room pack creates a (kept) room.
