# /validate — functional validation of a ticket

Validates a ticket's acceptance criteria against a live System Under Test and documents the results
back on the ticket. This is the **manual-validation leg** of the framework: its output (a run report
with evidence) is the source of truth a [`/automate`](automate.md) run turns into an automated
regression.

Product- and tenant-neutral: the ticket comes from the [ticket provider](../ticket/contract.md)
(Jira or mock-file), the system comes from the [SUT plugin](../sut/contract.md), and every Jira
field is resolved through [`jira.fields.json`](../ticket/providers/jira.fields.json).

## Invocation

```
/validate <TICKET-ID> [--sut <name>] [--env <environment>] [--depth minimal|standard|deep] [--profile <jira-profile>]
```

- `--sut`: the SUT plugin to validate against (default: the configured one).
- `--env`: target environment from the SUT manifest. If omitted, ask or reuse the session's last.
- `--depth`: validation depth; if omitted, decide via Quick Triage (Phase 1).
- `--profile`: the Jira field profile (default: the config's `active_profile`).

## Phase 1 — Setup

1. **Read policies + domain knowledge** (`policies/`, the SUT's `skills/` + `learnings/`) and **fetch
   the ticket** through the provider, in parallel. Normalize to `{id, title, description,
   acceptance_criteria[], status, comments[], links[], ...}`.
2. **Read comments** chronologically. Surface: AC/scope changes (show original vs comment AC and ask
   which to validate against), repro clarifications, MR/branch refs, prior results affecting scope.
3. **Quick Triage** → depth: *minimal* (single AC, narrow change), *deep* (≥4 ACs, multi-area,
   "refactor/migration/breaking"), *standard* otherwise. Log the choice + reason.
4. **Load matching learnings** for the area (SUT `learnings/` + any retrieval the host configures).
   Loading learnings is mandatory — they prevent repeated mistakes.

## Phase 2 — Environment

1. Select the environment from the SUT manifest (`--env` or the session default).
2. Collect the SUT's component/version info (cache per environment within a session; don't re-fetch).
3. Mask secrets (`***MASKED***`).

## Phase 3 — Validation (REST or UI)

1. **Each acceptance criterion becomes a check.** Parse them from the normalized ticket.
2. **Pick the verification surface per check** — the framework supports BOTH approaches:
   - **REST** (default, fastest): call the JSON API through the `SUTConnector` (`sut.get` / `sut.post`).
   - **UI** (when the criterion is about the front-end, or for genuine end-to-end): drive the site's
     web UI in a **real browser with Playwright**, against the SUT's `ui.path` (manifest). Prefer REST
     where an API path covers the criterion; use UI where the behaviour only exists in the UI, or when
     the ticket asks for an end-to-end check.
3. **Run UI checks headed so the QA person can WATCH the verification live** — a visible, slowed-down
   browser. With the framework's Playwright lane: `make ui-watch` (headed + `--slowmo`), or
   `poetry run pytest tests/test_ui.py --headed --slowmo 600 -n0`. (Headless is the default for
   automation; headed is for live human review.)
4. **Record PASS / FAIL / SKIPPED / BLOCKED** with specific detail for non-pass, per check.
5. **Summarize** in the test-execution-result format (see [`docs/report-formats.md`](../docs/report-formats.md)).
   Note which checks were REST vs UI — `/automate` uses that to pick the automated-test surface.

## Phase 4 — Write results to the ticket

Per the provider's approval gates (one approval per write). Determine the write target from the
profile's `write_results` (resolution-notes vs comment). Show *what / where / why*; wait for
approval (or proceed under `HARNESS_MODE=1`); write.

## Phase 5 — Transition

- **All checks passed:** resolve `transition.required_before_transition` fields first (ask if unset,
  showing options), behind their own approval; discover transitions dynamically; target a
  `transition.pass_target` status; apply only after a dedicated transition approval.
- **Any check failed:** do not transition. Document the failures; leave the ticket as-is. Optionally
  invoke [`/report-bug`](report-bug.md) for a real defect.

## Phase 6 — Report

1. **Save the run report** to `runs/<TICKET-ID>_<TIMESTAMP>.md` (the durable evidence a `/automate`
   run will cite).
2. **Append a learning** to the SUT's `learnings/` if the run produced a reusable pattern (durable,
   not a one-off run record), and publish it to the host's learnings store if configured.
3. **Save evidence** (screenshots/artifacts) under `runs/` and reference them in the report.

## On a failure

Hand off to [`/report-bug`](report-bug.md) for a real defect, or — when the failure is on an
*automated* test rather than the product — invoke the [review panel](../docs/multiagent/review-panel.md)
(R-DIAGNOSIS first) to classify test-bug vs real-bug before any fix.

## Error handling

- Provider call fails → report and stop; do not retry silently.
- Environment unreachable → mark environment-dependent checks BLOCKED.
- Approval declined → offer to adjust the content or abort.
