# restful-booker-live — the source-provisioning example (opt-in, networked)

The counterpart to `sut/restful-booker/` (an offline in-process mock). This site exists to
demonstrate the **SUT source-provisioning seam** against a *real* backend:

- `manifest.source.repo` points at the real upstream
  (`https://github.com/mwinteringham/restful-booker-platform`).
- `make sync-source SUT=sut/restful-booker-live` clones/refreshes it into `source/`
  (gitignored — see `.gitignore`), and `engine/freshness_gate.py` keeps it honest
  (local `HEAD` == `origin/HEAD`) before any lens cites it.
- `runtime.mode: remote` targets the live demo (`https://automationintesting.online`).

## Use it

```bash
make sync-source SUT=sut/restful-booker-live   # clone/refresh the real source locally
make freshness   SUT=sut/restful-booker-live   # verify the clone is in sync with origin
```

Then the review lenses (e.g. `r-mechanism`) can cite `sut/restful-booker-live/source/<file>:<line>`
against current upstream code when diagnosing a failure or scoping a feature.

## Scope / caveats

- **Opt-in.** It is *not* in the default offline gate or the CI matrices (`ALL_SITES` and both
  CI matrices list only `mock-shop` + `restful-booker`). Run it explicitly with
  `QAF_SITES=sut/restful-booker-live`.
- **Networked.** `sync-source` and any remote run require connectivity; keep them out of the
  deterministic offline gate.
- **Automated DESIGN/DIAGNOSE need a source adapter.** The upstream is a Java/Spring monorepo,
  not a Python module exposing `ROUTES` / `BUSINESS_RULES`, so `engine.design` /
  `engine.diagnostics` would need an adapter to read it (see `sut/contract.md`, "What the
  framework expects from the SOURCE"). The clone's value here is a fresh, citable real source.
