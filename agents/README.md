# Lens registry

The advisory review panel for Qensei. Each lens is a read-only subagent that
examines one failing or changed test and reports findings. The panel **raises the floor**;
it never lowers the bar and it never blocks a merge.

## The gate is not here

The single source of truth for "green" is the **deterministic regression gate**,
`engine/run.py` (it runs every pack against the SUT and exits non-zero if any case fails,
so CI can gate on it; `engine/runner.py` is the module it drives). The lenses below are
**advisory**: they help DIAGNOSE a Phase-4 failure and surface what a human should look at,
but **none of them can block a merge**. The human owns convergence — passing the panel means
the floor was raised, not that the work is done.

Every lens carries `gate: false`. This is structural, not a default: the panel is
advisory by construction.

## Entry-point vocabulary

- **Phase-4 loop** — the `/automate` validate-and-iterate loop, invoked on a freshly authored
  or changed test before/around a fix.
- **on-demand** — a human points the lens at a failed regression-gate run (`engine/run.py` /
  `make test`) or a CI log and asks the panel to adjudicate.
- **pre-commit** — runs as a lint after a test/pack edit, before the change lands. (The
  blocking pre-commit check is the *deterministic* spec-fidelity lint in `engine/fidelity_lint.py`,
  wired via `.pre-commit-config.yaml` + `.gitlab-ci.yml` + `make fidelity`; the advisory lens here is
  its judgement companion and does not block.)
- **plan-step** — reviews a plan's assumptions before the test is written.
- **migration-only** — runs only when porting a test from a legacy repo into this framework;
  not part of failure triage and not used in greenfield authoring.

## Registry

| Lens | Role (one line) | Enters | gate |
|------|-----------------|--------|------|
| **judge** | Adjudicates the lenses' findings — dedup, decide BLOCK / FIX / FLAG / ESCALATE per finding, run the rebuttal protocol, and write the decision-grade escalation digest for the human. | Phase-4 loop · on-demand | `false` |
| **r-diagnosis** | Diagnoses a failing case BEFORE any fix — classifies TEST_BUG / REAL_BUG / TRANSIENT / UNDOCUMENTED-ESCALATE with cited evidence; judgement-side complement to the deterministic `engine/diagnostics.py`. | Phase-4 loop · on-demand | `false` |
| **r-evidence** | Skeptic / anti-fabrication lens — verifies each causal claim and the gate state against the RAW source (the green dot is not evidence); runs the citation-resolution and SUT-source-freshness checks; surfaces cross-test, durable-collision, and env-divergence impact. | Phase-4 loop · on-demand | `false` |
| **r-mechanism** | SUT-mechanism lens — forces timing / SLA / scheduling / run-eligibility / coalescing / component-state reasoning into the open with exact `sut/<name>/source/<file>:<line>` citations, and surfaces every mechanism call for human review (CITED / UNCITED / MISREAD). | plan-step · Phase-4 loop · on-demand | `false` |
| **r-fidelity** | Spec-fidelity lens — catches edits that WEAKEN an acceptance criterion to turn a red test green (lowered thresholds, equality→inequality, dropped persona markers, ungated xfail, lost coverage); escalates restructured assertions (reshapes) for human confirmation, never auto-passing them. | Phase-4 loop (post-edit) · pre-commit · on-demand | `false` |
| **r-uplift** | Migration-uplift lens — verifies a ported legacy test adopted this framework's patterns (REST-first via the SUTConnector, typed facades, personas, soft-assert cases, self-cleaning) without importing legacy anti-patterns or dropping the behavioural contract the legacy test encoded. | migration-only | `false` |

## Notes

- **judge** presides; the other five are the lenses it adjudicates. **r-uplift** is the only
  lens outside the failure-triage panel — it runs in the migration variant only.
- Each lens is read-only (it writes only to its own memory dir), never files a ticket itself,
  and never weakens a spec: if the SUT genuinely cannot satisfy an acceptance criterion, the
  test is correctly red and the bug is real.
- The deterministic counterparts that *can* gate live in `engine/` — the regression gate
  (`engine/run.py`), the mechanical REAL_BUG-vs-TEST_BUG classifier (`engine/diagnostics.py`), the
  spec-fidelity lint (`engine/fidelity_lint.py`), the citation anti-fabrication gate
  (`engine/citation_gate.py`), and the source-freshness gate (`engine/freshness_gate.py`). The lenses
  in this directory complement those checks with judgement; they do not replace the gate and they do
  not become one.
