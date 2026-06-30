---
description: Turn a manually-tested ticket into a complete intent spec and an automated regression pack (REST-first, UI fallback), validated against the regression gate.
argument-hint: <TICKET-ID | "feature description">
---

# /spec-test

Convert a manually-validated feature into permanent regression coverage for the product
under test. The agent authors and maintains the spec and the regression pack; the human
owns intent and approval.

The framework is **domain-agnostic**: the product under test is wired in as a plugin under
`sut/<name>/`, and every access to it — calling its live runtime and reading its source —
goes through that plugin's **SUTConnector** (`engine/sut.py`). Nothing in this flow names a
specific backend; the active SUT plugin (`--sut sut/<name>`) supplies the routing.

**Input:** `$ARGUMENTS` — a **ticket id** resolved through the `ticket/` provider
abstraction (e.g. `QA-1234`), or a short feature description when there is no ticket.

## The entry flow — a ticket resolved through the `ticket/` provider abstraction

The unit of work is a manually-validated **ticket**. The framework never hard-codes a tracker:
it resolves the ticket through the `ticket/` **provider abstraction**, which exposes a uniform
read interface — `fetch(id) -> {id, title, description, acceptance_criteria, …}`.

- **JIRA is the reference provider**, but the **Jira field schema is configurable**: which Jira
  fields map onto `title` / `description` / `acceptance_criteria` / status is plugin config, so
  the framework works against any Jira project layout — and against any
  tracker that implements the provider interface.
- A **mock provider** (`sut/<name>/tickets/`) serves tickets offline — for the in-repo demo, for CI
  without a live tracker, and for SUT plugins whose tickets are illustrative (e.g. the `SHOP-*`
  tickets behind `mock-shop`).
- **No ticket?** A short feature description is accepted (the `noticket` path). Add the no-ticket
  notice to the spec (see `policies/methodology.md` § Spec File Conventions) and remind the human
  once that tracked work should have a ticket.
- **Read-only by default.** The provider *reads* tickets. *Filing* a ticket — e.g. the structured
  bug report the panel produces for a genuine backend regression — is an outward-facing,
  **human-gated** action routed through the same provider; this command never opens one.

## Spec vs plan

- **Spec (`sut/<name>/specs/<TICKET-ID|noticket>-<short-desc>.md`)** is the human-approved contract for
  *what* the test verifies: context, requirements, acceptance criteria, persona coverage, teardown.
  Reviewed once; changes go through human approval. (The methodology's `<NNN>-` counter is dropped
  here — the ticket id disambiguates, matching the existing `sut/<name>/specs/` and `sut/<name>/packs/` naming.)
- **Plan (`sut/<name>/plans/<YYYY-MM-DD>-<short-slug>.md`)** is the agent-iterated implementation: REST
  mapping, facade/fixture shape, persona markers, runtime expectations, SUT-shape rationale.
  Multiple plans can attach to one spec as the implementation evolves; the spec's final section
  lists its plans.

The three engine capabilities are all in play across the flow: **DESIGN** (`engine/design.py`)
seeds candidate coverage in Phase 1, **REGRESS** (`engine/run.py`) is the Phase 4 gate, and
**DIAGNOSE** (`engine/diagnostics.py`) drives the Phase 4 triage.

## Phase 0 — Orient

1. Read `README.md`, `docs/overview.md`, and the spec conventions in `policies/methodology.md`
   (§ Spec File Conventions), plus an existing spec under `sut/<name>/specs/` and any existing plan under
   `sut/<name>/plans/` for a related domain, as the shape to follow.
2. Read **both** knowledge stores for the relevant domain (append-only, AI-authored):
   - `policies/` — **framework-shape** patterns (fixture/case rules, gate/runner choices, persona
     discipline, test philosophy, ownership).
   - `sut/<name>/learnings/<DOMAIN>_LEARNINGS.md` + `sut/<name>/skills/` — **domain / system-shape**
     patterns for the active SUT plugin (what its endpoints do, where they drift, deploy/timing
     behaviour, the gotchas worth knowing before writing a case).
   Prior-session learnings prevent re-discovery of system-shape gotchas and framework-shape design
   rules — read them before writing or editing a case/fixture.
3. Read the active SUT plugin's manual-QA context — `sut/<name>/skills/*.md` — which describes how
   the feature is validated manually and where the contracts that matter for regression live.
4. **SUT-source freshness — MANDATORY GATE, before reading any SUT source.** Design and diagnostics
   read the backend SOURCE through the SUTConnector (`source_module()` / `source_path()`, i.e.
   `sut/<name>/source/`); a stale source means citing an old backend, which is a defect. The check
   depends on the plugin's `runtime.mode` (`manifest.json`):
   - **`in_process`** (the in-repo mock): the source *is* the running app and ships in this repo — it
     is **always fresh**; the gate is a no-op. Proceed.
   - **`remote`** (a real backend): the source is a checked-out clone. Verify it is current — each
     clone's local `HEAD` must equal its `origin/<default>` tip:
     ```bash
     # remote SUT only — SUT_DIR is the plugin dir passed to --sut (e.g. sut/acme)
     SUT_DIR=sut/<name>
     src="$SUT_DIR/$(python3 -c "import json;print(json.load(open('$SUT_DIR/manifest.json'))['source']['path'])")"
     b=$(git -C "$src" rev-parse --abbrev-ref HEAD)
     l=$(git -C "$src" rev-parse --short HEAD); r=$(git -C "$src" rev-parse --short "origin/$b")
     [ "$l" = "$r" ] && echo "✓ source @ $l" || echo "✗ $l != origin $r — refresh the clone before reading source"
     ```
     If the clone is STALE/DIRTY (or cannot be refreshed — VPN/SSH down), **STOP and surface it** to
     the human with the last-synced commit, rather than authoring against a stale clone. Only read
     `sut/<name>/source/` once the check is green. Enforcement is at the point of consumption.

## Phase 1 — Gather the manual scenario (background)

1. **Resolve the ticket via the `ticket/` provider** (read-only): pull its description and acceptance
   criteria through the configured field schema. (Mock provider when offline / no live tracker.)
2. Optionally run the manual validation as background — the **DESIGN** capability (`engine/design.py`
   reads `ROUTES` + `BUSINESS_RULES` from the SUT source and reports coverage gaps) plus the domain
   context in `sut/<name>/skills/`. Capture the resulting manual steps and findings; that run report
   becomes the "source of truth" for the spec's scenario section.
3. Separate fact (observed in the ticket / run) from inference. Note open questions.
4. **Ask persona coverage** (required): should this cover `existing_data` (durability / migration),
   `new_user` (fresh creation), or both? Record it in the spec's *Persona coverage* field and apply
   the matching persona on the case. Personas are defined in `policies/` (`new_user` = ephemeral,
   self-cleaning; `existing_data` = durable, find-or-create on a stably-named long-lived object that
   is never deleted).

## Phase 2 — Write the spec

1. Create `sut/<name>/specs/<TICKET-ID|noticket>-<short-desc>.md` following the conventions in
   `policies/methodology.md` and the shape of the existing `sut/<name>/specs/` specs.
2. Fill the spec sections — **intent only**: Context, Requirements, Acceptance Criteria (a `- [ ]`
   checkbox list of specific, testable, long-lived behavioral contracts), Persona coverage, Risks &
   Assumptions, Status. Include the **real-system (integration-boundary) AC**: at least one criterion
   must exercise the **real** SUT runtime (not a mock of it). Do NOT put REST endpoint mappings or
   file paths in the spec; those go in the plan (Phase 2b).
3. State acceptance criteria as long-lived, user-facing behavioral contracts — what the system does,
   not how it is wired internally.
4. **Surface the spec to the human for review before implementing** (Interactive Mode).

## Phase 2b — Write the plan

1. Create `sut/<name>/plans/<YYYY-MM-DD>-<short-slug>.md`. The slug names the spec topic.
2. Cover the *how*: a **REST mapping table** (for each manual step, the SUTConnector call —
   `sut.get(path)` / `sut.post(path, body)` — or the typed facade over it), facade/model extensions
   the plugin needs, the case/fixture shape, persona marker, and runtime expectations.
3. **Prefer the REST mapping.** For each manual step find the API equivalent and confirm
   endpoints/payloads against the **SUT source** via the SUTConnector (`source_module()` exposes
   `ROUTES` + `BUSINESS_RULES`; `source_path()` is the file). Use a UI/browser mapping only where no
   API path exists, or for genuine end-to-end coverage.
4. Reference the plan from the spec's final *Implementation* section.

## Phase 3 — Implement (translate the functional test to a REST **or** UI automated pack)

The validated functional test from `/test-ticket` is translated into a permanent automated test. The
**surface follows the verification**: criteria validated over the **REST API** become a REST pack;
criteria validated through the **web UI** become a UI (Playwright) pack. Many tickets yield one of
each. Pick per criterion, and prefer REST where an API path covers it (faster, less brittle).

**REST automated test** — a `RegressionCase` pack under `sut/<name>/packs/<TICKET-ID>-<short-desc>/`:

1. A `case.py` holding a `RegressionCase` subclass (`engine/case.py`) plus an index `README.md`.
2. The case declares the contract the DESIGN and DIAGNOSE layers read:
   - `id`, `title`, `spec_ref` (the `sut/<name>/specs/…` intent it satisfies);
   - `persona` — `new_user` or `existing_data`, per Phase 1;
   - `covers` — the backend surface it exercises (endpoints + business-rule ids), read by DESIGN;
   - `contract_claim` — the business-rule value the case relies on (e.g. `{rule, rate, min_qty}`),
     read by **`engine/diagnostics.py`** to tell REAL_BUG from TEST_BUG. Add it whenever the case
     pins a business rule — it is what makes a failure diagnosable.
3. `run(self, sut, expect)` calls the SUT **runtime** through the connector (`sut.get` / `sut.post`)
   with **soft assertions** (`expect.equal` / `expect.approx` / `expect.that`). Encode **behavioral
   contracts**, not internal call sequences.

**UI automated test** — a `UICase` pack under `sut/<name>/ui-packs/<TICKET-ID>-<short-desc>/`:

1. A `case.py` holding a `UICase` subclass (`engine/ui.py`) plus an index `README.md`. The SUT plugin
   must declare a `ui.path` in its manifest (where the web UI is served).
2. Same declarative metadata (`id`, `title`, `spec_ref`, `persona`, `covers`, `severity`), plus the
   `ui` tag so it runs in the opt-in UI lane (`make test-ui`).
3. `run(self, page, base_url, expect)` drives the front-end with a **real browser** — a Playwright
   `page` — and asserts on what the user sees (`page.goto`, `page.fill`, `page.click`,
   `page.wait_for_selector`, then `expect.that(...)`). Pin **stable element ids / roles**, not
   layout. `sut/restful-booker/ui-packs/BOOK-UI-1-book-a-room/` is the worked example.

**Both** are **self-cleaning** (`new_user` starts clean and leaves nothing behind; `existing_data`
find-or-creates a durable and never deletes it) and ship an index-card `README.md` (one-paragraph
summary, persona, `Spec:` link, `Covers:`, run command).

## Phase 4 — Validate (iterative, with the review panel)

Run the **regression gate** (`engine/run.py` / `make test`) against the **configured environments**
(`manifest.json` `env`) — not just the new case. A passing new case that broke an existing pack is a
net coverage loss; the gate is the source of truth, not a local single-pack run.

### 4a — Run the gate

1. Collect-clean locally (the case discovers and imports without error).
2. Run the gate locally as a smoke if you have the runtime/creds (the `in_process` mock boots itself;
   a `remote` plugin needs `.env`/Vault creds). Teardown must leave the environment as found.
3. Push to the feature branch and let CI run the gate across every configured environment. The full
   gate result across the configured environments is the validating signal — pull the **raw** CI job
   logs, not a summary checkmark.

### 4b — Triage every non-green result BEFORE any code change (the review panel)

Triage drives off **two complementary lenses**:

- **The deterministic code lens — `engine/diagnostics.py`.** It compares the case's `contract_claim`
  to the SUT's declared contract (`BUSINESS_RULES` via the SUTConnector source) and the runtime
  response, and mechanically emits `REAL_BUG` / `TEST_BUG` / `ENV_OR_TRANSIENT` / `INDETERMINATE`. Run
  it first when the case carries a resolvable `contract_claim`; its verdict is evidence, not an
  override.
- **The advisory review panel — the `agents/` lenses** (dispatched as subagents). It complements the
  heuristic for the judgment calls it cannot make. **Diagnose before any fix:**
  - **R-DIAGNOSIS** (`agents/r-diagnosis.md`) — finds the real cause (reading the case + `policies/` +
    `sut/<name>/learnings/` + the spec + the SUT source) BEFORE the generator changes anything;
    classifies `TEST_BUG` / `REAL_BUG` / `TRANSIENT` / `UNDOCUMENTED-ESCALATE`. The judgment-side
    complement to the deterministic lens (esp. serial-pass / parallel-fail exec-flow gaps).
  - **R-MECHANISM** (`agents/r-mechanism.md`) — verifies any claim about the SUT's internal
    mechanism / timing / scheduling / run-eligibility / component state against an exact SUT-source
    `file:line`; surfaces every mechanism call.
  - **R-EVIDENCE** (`agents/r-evidence.md`) — the skeptic: the green dot is not evidence; pulls the raw
    gate/CI state itself, runs the citation-resolution check, and flags cross-test / env-divergence /
    durable-collision impact.
  - **R-FIDELITY** (`agents/r-fidelity.md`) — the pre-commit fidelity lint: blocks an edit that
    **weakens** an acceptance criterion to turn a red test green; escalates restructured assertions
    (reshapes) for the human, never auto-passing them.
  - **R-UPLIFT** (`agents/r-uplift.md`) — **migration variant only** (porting a legacy test in); not
    used in greenfield spec authoring.
  - **JUDGE** (`agents/judge.md`) — adjudicates the lenses' findings (BLOCK / FIX / FLAG / ESCALATE),
    runs the rebuttal protocol, and writes the decision-grade escalation digest. Routes a genuine
    backend regression to a structured bug report for the **human** to file via the ticket provider
    (human-gated; the panel never files it).

  **The panel is advisory and NEVER gates the merge.** The regression gate (`engine/run.py`) remains
  the source of truth for "green"; the human owns convergence.

Classify each failure into one of the rows below. Surface the triage explicitly in the status update
so the human can override:

| Category | Signal in the trace | Allowed fix |
|---|---|---|
| New pack/case bug | The new case's assertion or fixture raises | Fix the case code, keep the assertion text identical |
| Regression on existing pack | An existing pack fails for the first time on this branch | Fix the new code or revert; existing coverage MUST stay green |
| Test design (scope/timing) | Assertion fires on aggregated state, not current-run state | Fix the scope (run id, time window, find-or-create handling); the assertion stays |
| SUT transient | 5xx, gateway timeouts, network blips | Add retry/backoff in the facade / connector layer; never touch the case |
| SUT sticky drift | Data state changed (a count grew, a durable mutated) | Rebaseline/refresh in the fixture; document as a learning; never relax |
| SUT genuine regression | Assertion fails for a real coverage gap on a healthy run (the deterministic lens's `REAL_BUG`) | **STOP. Escalate.** The case is correctly red. |
| Infrastructure | Runner ENOSPC, environment wedged, deploy in progress | **STOP. Escalate.** AI cannot fix infrastructure. |

**The validation objective stated in the spec NEVER changes during Phase 4.** Every fix preserves the
acceptance criteria **verbatim**. If a fix would require weakening a criterion, surface it to the human
as an explicit choice between (a) modifying the spec (requires re-approval) and (b) leaving the test
red. Forbidden without re-approval: relaxing `== 100` to `>= 90`, removing a persona marker, adding an
ungated `xfail` (no ticket-provider id), or increasing a timeout *to silence a real regression*. A
genuine rebaseline (a timeout too tight for legitimate growth) is a scope correction, not a weakening —
R-FIDELITY escalates the reshape; the human confirms it.

### 4c — Capture a learning every cycle

Each non-trivial cycle MUST produce at least one of:
- A new entry in `sut/<name>/learnings/<DOMAIN>_LEARNINGS.md` (domain / system-shape).
- A framework-shape pattern flagged for promotion to `policies/` (fixture/case rules, gate/runner
  choices, persona discipline).
- An explicit "no new learning — matches prior entry `<title>`" note in the status update.

Learnings are append-only, dated, in the canonical Context / Category / Learning / How-to-apply /
Example format, and must encode a **reusable** pattern — not a point-in-time run record (no hard-coded
ids, no load-dependent values). They make the next regression author's first cycle start where this
one's third cycle ended.

### 4d — Loop budget

After **3 cycles on the same root cause**, STOP iterating and escalate. The signature of a repeating
cause is: same triage category + same diagnostic signal in the trace + same class of code change.
Iterating past that is guessing; the human's context will close the gap faster than another cycle.
(Many cycles total are fine as long as each reveals a *new* root cause — repeated cycles on the *same*
cause are the stop signal. This mirrors the panel's `2× same finding → STOP` rule.)

### 4e — Exit

The loop ends when either:
- The gate is green on **every configured environment** AND no existing pack regressed → proceed to
  Phase 5.
- The loop budget is exhausted on the same root cause → escalate, do not merge.
- A triage category of **SUT genuine regression** or **infrastructure** was hit → escalate, do not
  merge.

## Phase 5 — Record

1. Write a validation report to `validation-reports/` (per `policies/methodology.md`).
2. Reconcile the spec (the non-skippable Phase 6.5 gate): re-read it, check each acceptance criterion
   against the implementation, set `## Status: COMPLETE` only if every box is checked, and link the
   pack + case id(s). Commit the spec in the same change as the pack.
3. Set the **pack's terminal status in-branch** — the pack `README.md` index card carries the status
   tag (e.g. `· automated`) at landing, as the single source of truth (do not defer it to a
   post-merge step). If the implementation took multiple iterations to converge, add sibling plans
   under `sut/<name>/plans/` capturing the rationale for each batch.
4. Finalize the pack `README.md` index card (summary, persona, `Spec:` link, `Covers:`, run command) —
   the card future agents read first.
5. Record any non-obvious SUT/API learning: domain / system-shape → `sut/<name>/learnings/`;
   framework-shape → flag for promotion to `policies/`.

## Guardrails

- **Both REST and UI are first-class automated-test surfaces.** Prefer the REST runtime API (via the
  SUTConnector) where an API path covers the criterion — it is faster and less brittle. Use a UI
  (Playwright `UICase`) pack where the behaviour lives in the front-end, where no API path exists, or
  for genuine end-to-end coverage. The surface follows what `/test-ticket` actually verified.
- **Never commit secrets;** credentials resolve through the plugin's `manifest.json` `creds`
  (env / Vault), never hardcoded.
- **Packs must clean up everything they create on shared environments** — `new_user` self-cleans;
  `existing_data` find-or-creates a durable and never deletes it.
- **The agent writes and maintains specs and packs; humans review and approve** — humans own intent,
  acceptance criteria, scope, and the go/no-go; the agent owns implementation.
- **The review panel is advisory and never gates the merge.** The regression gate (`engine/run.py`)
  is the source of truth for green; the human owns convergence; the spec's validation objective is
  never weakened to make a test pass.
