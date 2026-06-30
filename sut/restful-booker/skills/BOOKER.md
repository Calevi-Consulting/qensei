# BOOKER — domain knowledge (restful-booker)

Manual-QA context an agent uses to design and validate cases for this backend — the second
site's analog of `sut/mock-shop/skills/SHOP.md`. What the product does, where the contracts
live, and the gotchas worth knowing before writing a case. Faithful to mwinteringham's
restful-booker-platform (https://automationintesting.online).

## Surface (the real microservices, flattened by path prefix)
- **Auth** (`/auth/*`): `POST /auth/login {username,password}` → a session `token`
  (default creds **admin / password**); `POST /auth/validate`, `POST /auth/logout`.
- **Room** (`/room/*`): `GET /room/` → `{rooms:[...]}`; `GET /room/{id}`; `POST /room/`
  creates a room (`roomName`, `type` ∈ Single/Double/Twin/Family/Suite, `roomPrice`, …).
- **Booking** (`/booking/*`): `POST /booking/` creates a booking
  (`roomid`, `firstname`, `lastname`, `depositpaid`, `bookingdates:{checkin,checkout}`, …);
  `GET /booking/`, `GET /booking/{id}`, `GET /booking/summary?roomid=`, `DELETE /booking/{id}`.
- **Message** (`/message/*`): `POST /message/` submits a contact message.

## Contracts that matter for regression
- **no-double-booking** (REAL platform rule): a booking whose dates **overlap** an existing
  booking on the same room is rejected with **HTTP 409**; `checkin >= checkout` is likewise
  **409**. This is the highest-value behaviour to protect — it is the core availability promise.
- **longstay-discount** (illustrative rule the mock adds): a stay of **≥ 7 nights** gets
  **15% off** the room subtotal (`roomPrice × nights`). It exists to exercise the diagnosable
  REAL_BUG/TEST_BUG seam (the booking response carries `subtotal`/`discount`/`totalprice`); the
  authoritative values live in the source as `LONGSTAY_RATE` / `LONGSTAY_MIN_NIGHTS` and in
  `BUSINESS_RULES['longstay-discount']`. The live platform has no price field — see the mock note.

## Auth model
- The real platform authenticates **writes** with a session `token` from `POST /api/auth/login`
  (returned in the JSON body on the current deployment; classically a `token` cookie). The
  framework resolves this through the plugin's `resolve_creds` (`creds.mode = provider`, enabled
  per-run with `QAF_CREDS_MODE=provider`); `resolve_creds` reads the token from a Set-Cookie or the
  body. The **mock does not enforce auth**, so the offline gate is dependency-free; only the `live`
  env needs the login.

## Local mock vs the live site
- Default (`--sut sut/restful-booker`, no `--env`): boots the in-repo mock in-process —
  deterministic, offline, the merge gate.
- `QAF_ENV=live`: the manifest's `live` env overrides the runtime to `remote` and points at the
  real API under `https://automationintesting.online/api`. Add `QAF_CREDS_MODE=provider
  QAF_USERNAME=admin QAF_PASSWORD=password` to authenticate writes. **Scope:** the live env
  exercises the remote-connection + login seam and the behavioural rules the real platform
  implements (e.g. the **409** on overlapping dates, BOOK-3). Packs asserting the mock's computed
  price fields (`subtotal`/`discount`/`totalprice` — the real booking model has none) are
  mock-scoped; the offline mock remains the deterministic gate.

## UI testing (Playwright)
- The mock serves a minimal booking **web UI** at `GET /ui` (manifest `ui.path`): a form that loads
  rooms from `GET /room/` and submits to `POST /booking/`, then shows a `#confirmation` (or `#error`).
  It is the deterministic, offline stand-in for the real site's front-end.
- UI packs live in `sut/restful-booker/ui-packs/` as `UICase`s (`engine/ui.py`) and drive the page
  with a real browser: `BOOK-UI-1` books a room through the form. Run `make test-ui` (headless) or
  `make ui-watch` (headed + slow, to watch live). They run in the opt-in `ui` lane, not the REST gate.
- Pin **stable element ids** (`#firstname`, `#room`, `#book-btn`, `#confirmation`), not layout. An
  `<option>` is never "visible" to Playwright — wait for it with `state="attached"`.

## Gotchas
- **Dates are half-open**: a stay is `[checkin, checkout)`; `nights = checkout − checkin`. The
  overlap test must pin a TOUCHING booking (one's checkout == the next's checkin) as *allowed*
  and a genuinely overlapping one as *rejected* — the off-by-one magnet for availability.
- The mock requires the **room to exist** before booking (so it can price the stay); the live
  booking service is laxer. Book against a seeded/created room.
- Bookings are **ephemeral** (cleared by the `/booking/reset` isolate seam before each case);
  rooms are **durable** (file-backed, persist across boots) — that is what the `existing_data`
  durable-room pack relies on.
