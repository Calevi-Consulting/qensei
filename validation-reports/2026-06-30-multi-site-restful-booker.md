# Validation Report — multi-site support + restful-booker site + selectable CI

**Date:** 2026-06-30
**Spec:** sut/restful-booker/specs/BOOK-1..3 + BOOK-DUR (per-site specs, all COMPLETE)
**Branch:** main (working tree)
**Scope:** Make the framework work on different sites with isolated automated tests per site;
add `restful-booker` as a second site; add CI/CD that can choose which site to validate.

## What changed

- **Per-site test isolation (engine seam).** A manifest `tests` block (`packs`/`specs`/`tickets`)
  resolved per-SUT in `SUTConnector` (`packs_dir`/`specs_dir`/`tickets_dir`). `engine/run.py` and
  `engine/design.py` default `--packs` to the SUT's own packs dir, so a site's gate discovers only
  its own cases. `engine/fidelity_lint.py` scans `sut/*/packs/*/case.py`. Added `runtime_mode()`
  (an env may override mode → one plugin boots an in-process mock locally and connects to a remote
  `live` env) and a `QAF_CREDS_MODE` per-run override.
- **mock-shop made self-contained.** Moved `packs/`, `core/specs/`, `ticket/mock/`, `examples/`
  under `sut/mock-shop/` (history-preserving `git mv`); fixed all internal cross-links.
- **restful-booker site (new).** A faithful zero-dependency stdlib mock of
  mwinteringham's restful-booker-platform (auth/room/booking, the real 409 no-double-booking rule,
  an illustrative long-stay discount for the diagnosable seam), a manifest with `local` + `live`
  envs, a `plugin.py` (cookie-login provider + `rooms_available` pre-flight), skills, learnings, and
  4 packs (BOOK-1 create, BOOK-2 long-stay discount [diagnosable], BOOK-3 no-double-booking,
  BOOK-DUR durable room) + specs + a mock ticket + a TEST_BUG example + a bug-report example.
- **Selectable CI/CD.** New `.github/workflows/qa-gate.yml` (the repo is on GitHub and had no
  Actions workflow): push/PR validate every site; a `workflow_dispatch` `site` dropdown picks one or
  all. `.gitlab-ci.yml` made site-selectable (a `SITE` variable runs one site; default runs all).
- **Tooling/docs.** `new_pack.py` and `regen_index.py` made SUT-aware; `.pre-commit-config.yaml`
  glob; Makefile per-site vars + `demo-booker`; README / overview / architecture / sut-contract /
  ticket-contract / command + agent + gate docs updated to the per-site layout.

## Phase 3 — Tests

- `make test-engine`: **40 passed** (was 30; +10 in `tools/tests/test_multisite.py`).
- New integration-boundary coverage (booted, real runtime): the booker mock is booted in-process and
  its gate runs green; site-isolation (one site's gate never discovers another's cases); seed-bug →
  REAL_BUG and bad-test → TEST_BUG; the provider cookie-login flow against the booted mock.
- `make test SUT=sut/mock-shop` → 3/3; `make test SUT=sut/restful-booker` → 4/4.
- `make demo` and `make demo-booker` → design + gate + REAL_BUG + TEST_BUG all correct on both sites.
- `make fidelity` (both sites): no weakenings. `make secrets`: clean.

## Phase 4 — Code quality

- Fixed a latent socket leak in `SUTConnector.stop()` surfaced by the new booted tests
  (`server_close()` now releases the listening socket); test suite runs clean under
  `-W error::ResourceWarning`.
- The booker mock mirrors mock-shop's structure (no new abstraction); diagnostics/design/personas
  seams reused unchanged — the proof the second site needed no engine change.

## Phase 5 — Security

- No real secrets: `admin`/`password` are the platform's published public demo credentials; the mock
  session token is a static placeholder. `make secrets` gate: clean.
- No eval/shell/SQL; the mock parses JSON + ints only. CI passes the dispatch input via `env:` (not
  script interpolation); the only input is a fixed `choice`. `plugin.py` logs in to a fixed constant
  or operator-set `base_url` (no untrusted input). Zero third-party deps → no CVE surface.

## Phase 5.5 — Release safety

- Reversible: `git revert` of the change restores the prior single-site layout (the `git mv`s and
  engine edits are self-contained). The booker durable store (`.rooms.json`) is gitignored runtime
  state. No data migration. CI additions are inert until triggered.

## Adversarial review + fixes

An independent adversarial review (subagent) audited the isolation seam, the booker mock, the
plugin, the packs, and the CI. No HIGH defects. Two MED + two LOW were found and **fixed**:

- **MED-1 — live env unreachable / mis-scoped.** The real demo moved its API under `/api`
  (verified: `POST /auth/login` → 404, `POST /api/auth/login` → 200) and is fronted by Cloudflare,
  which 403s the default stdlib User-Agent. Fixed: `env.live.base_url` + `plugin.LIVE_URL` now carry
  `/api`; added a default browser `User-Agent` (overridable via `QAF_USER_AGENT`) so a WAF-fronted
  real site does not 403 the client. **Verified end-to-end against the live site**: `resolve_creds`
  logs in (200 + token) and `GET /api/room/` returns the real 3 rooms. Documented honestly that the
  discount/price packs are mock-scoped (the real booking model has no price field) while the 409
  availability rule is live-faithful.
- **MED-2 — mock crashed (dropped socket) on malformed input** instead of returning 4xx (non-int
  `roomid`/`roomPrice`/query, non-object `bookingdates`). Fixed: `_as_int` / `_parse_date` guards →
  clean 400s; overlap now compares `datetime.date` objects (kills the LOW lexicographic-date edge).
  Locked by a new `test_malformed_input_gets_4xx_not_a_crash`.
- **LOW** — stale Set-Cookie comment corrected (token may come via cookie or JSON body; the plugin
  already handled both). BOOK-DUR's name-based teardown left as-is (never executes behind the
  `is_protected_name` no-delete guard; mirrors mock-shop's SHOP-DUR for consistency).

Re-verified after fixes: **41 tests pass** (+1), both gates green, both demos' REAL_BUG/TEST_BUG
correct, fidelity + secrets clean, 0 broken links, live login + room read confirmed against the
real site.

## Result

All gates green on both sites; the framework now tests tickets of one site or another, CI can
validate a chosen site, and the booker `live` env connects + authenticates against the real public
API. Not yet committed — awaiting review.
