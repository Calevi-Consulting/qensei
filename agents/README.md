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
| **r-evidence** | Skeptic / anti-fabrication lens — verifies each causal claim and the gate state against the RAW source (the green dot is not evidence); runs the citation-resolution and SUT-source-freshness checks (for a sourceless SUT, resolves against the in-repo ticket/doc snapshot); surfaces cross-test, durable-collision, and env-divergence impact. | Phase-4 loop · on-demand | `false` |
| **r-mechanism** | SUT-mechanism lens — forces timing / SLA / scheduling / run-eligibility / coalescing / component-state reasoning into the open with exact `sut/<name>/source/<file>:<line>` citations (or ticket/doc-snapshot anchors for a sourceless SUT), and surfaces every mechanism call for human review (CITED / UNCITED / MISREAD). | plan-step · Phase-4 loop · on-demand | `false` |
| **r-fidelity** | Spec-fidelity lens — catches edits that WEAKEN an acceptance criterion to turn a red test green (lowered thresholds, equality→inequality, dropped persona markers, ungated xfail, lost coverage); escalates restructured assertions (reshapes) for human confirmation, never auto-passing them. | Phase-4 loop (post-edit) · pre-commit · on-demand | `false` |
| **r-coverage** | Coverage-fidelity lens — verifies the pack EXERCISES every acceptance criterion the spec states, and that its `covers` / `contract_claim` resolve to real ROUTES / BUSINESS_RULES in the SUT source (the mapping DESIGN reports over and DIAGNOSE relies on); complements r-fidelity by catching under-coverage and dangling metadata (COVERED / GAP / CLAIM-MISMATCH); for a **sourceless** SUT, `covers` / `contract_claim` cannot resolve against source, so it flags `UNVERIFIED (sourceless)` rather than `CLAIM-MISMATCH` (AC-exercise coverage still applies). | Phase-4 loop (post-edit) · on-demand | `false` |
| **r-uplift** | Migration-uplift lens — verifies a ported legacy test adopted this framework's patterns (REST-first via the SUTConnector, typed facades, personas, soft-assert cases, self-cleaning) without importing legacy anti-patterns or dropping the behavioural contract the legacy test encoded. | migration-only | `false` |

## Notes

- **judge** presides; the other six are the lenses it adjudicates. **r-uplift** is the only
  lens outside the failure-triage panel — it runs in the migration variant only.
- Each lens is read-only (it writes only to its own memory dir), never files a ticket itself,
  and never weakens a spec: if the SUT genuinely cannot satisfy an acceptance criterion, the
  test is correctly red and the bug is real.
- **Read-only is tool-enforced, not just prose.** Each lens frontmatter grants a minimal
  `tools: Read, Grep, Glob, Bash` allowlist (Write/Edit are never granted) plus a
  `disallowedTools: Write, Edit, MultiEdit, NotebookEdit` belt. Verified empirically in a fresh
  Claude Code session on **both** invocation paths (`claude --agent <lens>` and a `subagent_type`
  spawn via the Agent tool): the lens comes back with a read-only toolset and Write/Edit absent.
  Two caveats worth knowing:
  - The restriction is applied when the agent is loaded **at session start**. Wiring the panel
    into `.claude/agents` *mid-session* (e.g. the first `make install` run inside a live Claude
    session) registers the lenses but does NOT apply their tool limits until Claude Code is
    restarted — a mid-session-discovered lens transiently has the full toolset.
  - `Bash` stays granted because the lenses need read-only shell (git, `engine/run.py`). A lens
    could therefore still write via the shell; that residual is bounded by the read-only prompt
    discipline, not tool-blocked. The tool-level guarantee is against Write/Edit (and, by the
    `disallowedTools` belt, the notebook/multi-edit variants), not against Bash-driven writes.
- The deterministic counterparts that *can* gate live in `engine/` — the regression gate
  (`engine/run.py`), the mechanical REAL_BUG-vs-TEST_BUG classifier (`engine/diagnostics.py`), the
  spec-fidelity lint (`engine/fidelity_lint.py`), the citation anti-fabrication gate
  (`engine/citation_gate.py`), and the source-freshness gate (`engine/freshness_gate.py`). The lenses
  in this directory complement those checks with judgement; they do not replace the gate and they do
  not become one.
