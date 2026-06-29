# Functional ticket testing & reporting

Two QA capabilities the framework provides on top of the regression engine, both driven through
the same plugin seams — the **SUT plugin** for the system under test, the **ticket provider** for the
tracker:

- **Functional ticket validation** — take a ticket, validate its acceptance criteria against the
  live system **over REST or the UI**, record the result, and (optionally) transition the ticket.
  REST checks go through the `SUTConnector`; UI checks drive a real browser with **Playwright**, run
  **headed** so a QA person can watch the verification live (`make ui-watch`).
- **Bug / ticket reporting** — turn a confirmed failure into a structured bug report, human-gated
  before anything is filed.

`/automate` then turns the validated result into a permanent automated test on the **same surface it
was verified on** — a REST `RegressionCase` pack or a UI `UICase` (Playwright) pack.

Both are tracker- and product-neutral: the tracker layout is per-tenant config
(`ticket/providers/jira.fields.json`), and the system under test is a SUT plugin — so the same flows
run on any product and any Jira layout with no command changes.

## Capabilities

| Capability | Where | Notes |
|------------|-------|-------|
| Validate a ticket's ACs live → record results → transition → report | [`commands/validate.md`](../commands/validate.md) | ticket via the provider abstraction; system via the SUT plugin |
| Structured bug / improvement report | [`commands/report-bug.md`](../commands/report-bug.md) | investigation + a fixed-section report + a human approval gate |
| Per-tenant Jira field mapping | [`ticket/providers/jira.md`](../ticket/providers/jira.md) + [`jira.fields.json`](../ticket/providers/jira.fields.json) | normalized field names → a tenant's real ids/paths/strategies; swap tenants by selecting a profile (`default`, `acme`, …) |
| Report formats (bug + result) | [`report-formats.md`](report-formats.md) | the durable shapes both commands emit |
| Approval gates, secret masking, severity, learnings | [`policies/`](../policies/) + provider gates | governance, not hardcoded behaviour |

## Open enhancements (none blocks the core flows)

- **Severity scale** — `report-bug` references severity, but a generic scale (Low / Minor / Major /
  Critical + mapping guidance) is not yet a policy. → add `policies/severity.md` or a `severity`
  block in a tenant profile.
- **Learnings sink** — `validate` can publish run learnings if a store is configured, but no
  concrete sink ships yet. → wire a pluggable learnings store.
- **Lightweight task creation** — partially covered by `report-bug --type improvement`; a dedicated
  thin "create a task" command is optional.
- **Broad UI-surface crawl** — a generic multi-page UI-validation helper is optional; useful once a
  UI-driving SUT plugin exists.
- **Observability correlation on failure** — "if an observability provider is configured, correlate
  logs/traces on a failure" is a pluggable future, not yet implemented.

## Out of scope (by design)

Release coordination, chat/Slack notifications, CI/pipeline analysis, and infrastructure/auth dev
tooling are not part of these two capabilities. The regression gate (`engine/run.py`) is the
framework's automation surface; product-specific domain knowledge belongs in a SUT plugin's
`skills/` / `learnings/`, not the product-neutral core.
