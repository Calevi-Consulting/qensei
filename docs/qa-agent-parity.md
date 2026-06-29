# qa-agent parity — functional testing & ticket reporting

Completeness check: does qa-framework cover what qa-agent has for **functional testing of a ticket**
and **ticket/JIRA reporting**, keeping the logic but usable on a non-AIQ product and a different Jira
field layout? Scope is those two areas only — release/Slack/CI/infra and AIQ domain skills are out of
scope by design and listed at the bottom.

## In-scope capabilities

| qa-agent | qa-framework | status |
|----------|--------------|--------|
| `/test-ticket` (validate ACs live → write results → transition → report) | [`commands/test-ticket.md`](../commands/test-ticket.md) | **COVERED** — phases preserved; ticket via provider, system via SUT plugin |
| `/report-bug` (Bug/Improvement, structured) | [`commands/report-bug.md`](../commands/report-bug.md) | **COVERED** — investigation + 6/3-section report + approval gates preserved |
| `skills/JIRA.md` (access, approval gates, required fields, **AIQ custom-field ids**) | [`ticket/providers/jira.md`](../ticket/providers/jira.md) + [`jira.fields.json`](../ticket/providers/jira.fields.json) | **COVERED + genericized** — hardcoded ids → per-tenant config (`default` + `aiq` profiles) |
| `skills/BUG_REPORT_FORMAT.md` | [`docs/report-formats.md`](report-formats.md) (bug format) | **COVERED** |
| `skills/TEST_OUTPUT.md` | [`docs/report-formats.md`](report-formats.md) (result format) | **COVERED** |
| `skills/PLATFORM_VERSIONS.md` (version block) | SUT manifest version collection + the Environment section | **COVERED** as a SUT-plugin concern (AIQ browser endpoints → the plugin's job) |
| `QA_CORE.md` (approval gates, secret masking, severity, learnings) | `policies/` (methodology, input-hygiene, communication) + provider gates | **COVERED**, except the **severity scale** (see gaps) |

## Real gaps still to fill (small, named — none block the core ask)

- **Severity classification scale** — `report-bug` references severity, but a generic scale (Low/
  Minor/Major/Critical + mapping guidance) is not yet written. → add `policies/severity.md` or a
  `severity` block in a profile.
- **Learnings publish sink** — `test-ticket` Phase 6 says "publish to the host's learnings store if
  configured", but no concrete sink exists yet (the same loop the design briefing flagged). → wire a
  pluggable learnings store.
- **`create-internal-task`** (a lightweight "create a Task") — partially covered by `report-bug
  --type improvement`; a dedicated thin command is not ported. Optional.
- **`/crawler`** (broad multi-page UI-surface validation) — a generic UI-crawl helper is not ported.
  Optional; useful once a UI-driving SUT plugin exists.
- **Datadog log correlation** (`--datadog`) — AIQ observability specific; the generic form is "if an
  observability provider is configured, correlate on failure". Pluggable future, not ported.

## Deliberately out of scope (not "functional test + ticket report")

- **Release/coordination:** `release-notes`, `post-release-*-slack`, `RELEASE_COORD`, `HIM_RELEASE`.
- **CI/automation:** `pipeline-analysis`, `qa-automation`, `compare-scenarios`, `compare-ui`,
  `test-agent`, `sanity`, `sanity-ready3` — the regression gate (`engine/run.py`) is the framework's
  automation surface.
- **Infra/auth/dev tooling:** `ssh-onprem`, `reauth-atlassian`, `reauth-gitlab`, `commit-in-branch`,
  `lint-fix`, `update-codebase`.
- **AIQ domain knowledge:** the `AI_*`, `AGENTS`, `BE`, `UI`, `INTEGRATIONS`, `IM_K8S`,
  `CODEBASE_ACCESS`, `REMOTE` skills — these belong in a **SUT plugin's** `skills/`/`learnings/`, not
  the product-neutral framework. (mock-shop carries its own `skills/SHOP.md`.)

## Verdict

The two requested areas — functional ticket validation and ticket/JIRA reporting — are **covered**,
with the AIQ-hardcoded Jira fields genericized into a per-tenant config. The remaining gaps are
small, named, and optional; none is required for the framework to run those flows on a non-AIQ Jira.
