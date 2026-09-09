export const meta = {
  name: 'review-panel',
  description:
    'Run the review panel on ONE failing/changed test of a Qensei SUT: ORIENT reads the record, the deterministic engine.diagnostics runs when a pack is named, R-DIAGNOSIS diagnoses before any fix, flagged R-EVIDENCE/R-MECHANISM verify in parallel, engine.citation_gate resolves every citation, JUDGE adjudicates. Implements docs/multiagent/review-panel.md with the agents/ lenses (agentType).',
  phases: [
    { title: 'Orient', detail: 'read the record first — index-card gotchas, spec ACs, learnings, prior reports' },
    { title: 'Diagnose', detail: 'engine.diagnostics (mechanical, when a pack is named) then R-DIAGNOSIS — before any fix' },
    { title: 'Triage', detail: 'R-EVIDENCE / R-MECHANISM — conditional on R-DIAGNOSIS’s flags, in parallel' },
    { title: 'Adjudicate', detail: 'engine.citation_gate over the findings, then JUDGE' },
  ],
}

// Input via Workflow `args`: { sut, failure, env, pipeline, spec, diff, pack, seed_bug } — `sut` required,
// plus at least one subject field.
//
// SUBJECT GATE — fail loud rather than convene a blind panel. A caller who passes `args` as a STRING (the
// natural mistake: every field of the brief is prose) would fall through `typeof args === 'object'` to `{}`
// and the panel would run every lens against a subject of nulls, returning an authoritative-looking
// ESCALATE whose real content is "no subject was supplied" — and its citation gate would pass VACUOUSLY,
// exit 0 over an empty claim set, which reads like a clean bill of health. A silent degradation that
// manufactures a confident verdict is worse than an error, so this throws: a workflow error cannot be
// mistaken for an adjudication. (The repo's own rule — a policy without a gate is not followed — applied to
// the orchestrator itself: the README documenting the shape is not the missing piece; the check at the
// point of consumption is.)
if (typeof args === 'string') {
  throw new Error(
    'review-panel: `args` must be an OBJECT { sut, failure, env, pipeline, spec, diff, pack }, not a string. ' +
      'Put the failure brief in `args.failure` and re-invoke. Received a string of length ' +
      `${args.length}, which would have produced an all-null subject and a blind panel.`,
  )
}
const ctx = args && typeof args === 'object' ? args : {}
const SUT = typeof ctx.sut === 'string' ? ctx.sut.trim() : ''
if (!SUT) {
  throw new Error(
    'review-panel: `args.sut` is required (e.g. "sut/mock-shop"). Every lens reads the System Under Test ' +
      'through that plugin’s SUTConnector — freshness, source citations and the diagnostics oracle are ' +
      'all per-SUT, so a panel without one would cite nothing and verify nothing.',
  )
}
const SUBJECT_KEYS = ['failure', 'env', 'pipeline', 'spec', 'diff', 'pack']
const provided = SUBJECT_KEYS.filter((k) => {
  const v = ctx[k]
  return v !== null && v !== undefined && String(v).trim() !== ''
})
if (provided.length === 0) {
  throw new Error(
    'review-panel: no subject. At least one of { failure, env, pipeline, spec, diff, pack } must be ' +
      'non-empty — the panel reviews ONE failing/changed test and cannot invent one. Supply a failing case ' +
      'id + gate output, or a pack dir, or (for a changed-test review) a spec id + diff.',
  )
}
log(`SUT ${SUT}; subject fields supplied: ${provided.join(', ')}`)

const PACK = typeof ctx.pack === 'string' && ctx.pack.trim() !== '' ? ctx.pack.trim() : null
// `seed_bug` reproduces a regression with the framework's own seeding flag (`engine.diagnose --seed-bug`,
// what `make diagnose-realbug` runs). Without it the mechanical step re-runs a HEALTHY pack and reports
// NO_FAILURE, which would contradict a failure brief describing a regression — so a caller reviewing a
// seeded regression must say so. It only ever affects the deterministic step's command line.
const SEED_BUG = ctx.seed_bug === true
const subject = JSON.stringify(
  {
    sut: SUT,
    pack: PACK,
    seed_bug: SEED_BUG,
    failure: ctx.failure ?? null,
    env: ctx.env ?? null,
    pipeline: ctx.pipeline ?? null,
    spec: ctx.spec ?? null,
    diff: ctx.diff ?? null,
  },
  null,
  2,
)

const ORIENT_SCHEMA = {
  type: 'object',
  properties: {
    sources_read: {
      type: 'array',
      items: { type: 'string' },
      description: 'repo-relative paths ACTUALLY read, with line ranges where it matters',
    },
    documented_disposition: {
      type: 'string',
      description:
        'Standing disposition already recorded for this red, verbatim if present (e.g. "leave RED, the backend is retired"), else "none found".',
    },
    rejected_fixes: {
      type: 'array',
      items: { type: 'string' },
      description: 'fixes already considered and REJECTED as weakening — a lens must not re-propose these',
    },
    known_traps: {
      type: 'array',
      items: { type: 'string' },
      description: 'gotchas already paid for, from the pack index cards and learnings',
    },
    prior_attempts: {
      type: 'string',
      description: 'how many times this same failure was already "fixed", and how each attempt failed — the loop-budget input',
    },
    acceptance_criteria: {
      type: 'array',
      items: { type: 'string' },
      description: 'the acceptance criteria the subject case carries, which no proposal may weaken',
    },
    contradicts_subject: {
      type: 'array',
      items: { type: 'string' },
      description: 'anything in the record that CONTRADICTS a premise stated in the subject brief',
    },
  },
  required: ['sources_read', 'documented_disposition'],
}

const DIAGNOSTICS_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', description: 'the verdict engine.diagnose printed, verbatim' },
    rule: { type: 'string', description: 'the contract rule id it resolved, or "" when none' },
    raw: { type: 'string', description: 'the command’s stdout+stderr, verbatim' },
    exit_code: { type: 'number' },
  },
  required: ['verdict', 'raw'],
}

const DIAG_SCHEMA = {
  type: 'object',
  properties: {
    verdict: {
      type: 'string',
      enum: ['TEST_BUG', 'REAL_BUG', 'ENV_OR_TRANSIENT', 'INDETERMINATE', 'UNDOCUMENTED-ESCALATE'],
    },
    summary: { type: 'string' },
    citation: { type: 'string', description: 'sut/<name>/source/<file>:<line> (or a ticket/doc anchor for a sourceless SUT)' },
    fix_direction: { type: 'string' },
    needs_mechanism: { type: 'boolean' },
    needs_evidence: { type: 'boolean' },
    source_stale: { type: 'boolean', description: 'true when the SUT-source freshness self-gate reported STALE/DIRTY' },
  },
  required: ['verdict', 'summary', 'needs_mechanism', 'needs_evidence'],
}

const EVIDENCE_SCHEMA = {
  type: 'object',
  properties: {
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          verdict: { type: 'string', enum: ['SUPPORTED', 'UNSUPPORTED', 'CONTRADICTED'] },
          evidence: { type: 'string' },
        },
        required: ['claim', 'verdict'],
      },
    },
    cross_test_findings: { type: 'array', items: { type: 'string' } },
  },
  required: ['claims'],
}

const MECHANISM_SCHEMA = {
  type: 'object',
  properties: {
    mechanism_claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          verdict: { type: 'string', enum: ['CITED', 'UNCITED', 'MISREAD'] },
          citation: { type: 'string' },
        },
        required: ['claim', 'verdict'],
      },
    },
    surfaced_for_human: { type: 'array', items: { type: 'string' } },
  },
  required: ['mechanism_claims'],
}

const CITATION_GATE_SCHEMA = {
  type: 'object',
  properties: {
    exit_code: { type: 'number', description: '0 = all resolve / none cited; 1 = FABRICATED; 3 = UNVERIFIABLE (source absent)' },
    fabricated: { type: 'array', items: { type: 'string' }, description: 'citations whose path or line does not exist in a PRESENT source' },
    unverifiable: { type: 'array', items: { type: 'string' }, description: 'citations whose owning source is not fetched' },
    raw: { type: 'string', description: 'the gate’s output, verbatim' },
  },
  required: ['exit_code', 'raw'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    decision: { type: 'string', enum: ['BLOCK', 'FIX', 'FLAG', 'ESCALATE', 'PANEL_CLEAR'] },
    digest: { type: 'string' },
    per_finding: {
      type: 'array',
      items: {
        type: 'object',
        properties: { finding: { type: 'string' }, decision: { type: 'string' }, rationale: { type: 'string' } },
      },
    },
    bug_report: { type: 'string', description: 'on REAL_BUG: the structured report for the HUMAN to file via the ticket provider' },
  },
  required: ['decision', 'digest'],
}

// ---- Phase 0: ORIENT — read the RECORD before anyone reasons about the failure ----
// Deliberately NOT a lens: it makes no judgement and returns no verdict. It returns what the repo already
// knows so the lenses argue against it instead of rediscovering it, and it is the JUDGE's loop-budget
// input (`prior_attempts` is how the JUDGE knows this is rewrite #3). Best-effort by design: if it returns
// nothing the panel proceeds, and every downstream prompt says so.
phase('Orient')
const orient = await agent(
  `READ-ONLY orientation for a Qensei review panel. Do NOT diagnose, do NOT propose a fix, do NOT judge — ` +
    `you are assembling the RECORD the lenses must argue against.\n\n` +
    `Read what this repo already knows about the subject below, preferring PRIMARY sources over inference:\n` +
    `- the pack index card \`${PACK ?? `${SUT}/packs/<id>`}/README.md\` — its summary and any "Gotcha" notes ` +
    `(these encode failures already paid for);\n` +
    `- the spec the case's \`spec_ref\` points at, under \`${SUT}/specs/\` — the acceptance criteria, which ` +
    `no proposal may weaken;\n` +
    `- any plan under \`${SUT}/plans/\` naming the pack, including its \`## Design panel\` record (findings ` +
    `already DEFERRED or REJECTED at design time);\n` +
    `- \`${SUT}/learnings/*.md\` (domain / system-shape) and \`${SUT}/skills/*.md\`;\n` +
    `- \`policies/\` for framework-shape rules (personas, test philosophy);\n` +
    `- \`validation-reports/*\` mentioning the pack or the failing case, including their \`### Panel\` lines;\n` +
    `- the case source itself (\`case.py\`), to list the real acceptance criteria and assertions involved.\n\n` +
    `Report ONLY what you actually read — \`sources_read\` must list real repo-relative paths; an empty ` +
    `record is a valid and useful answer ("none found"). Do not invent a disposition.\n\n` +
    `Two fields matter most. \`rejected_fixes\`: approaches the record already REJECTED as weakening a ` +
    `criterion — a lens re-proposing one wastes a whole cycle. \`contradicts_subject\`: anything in the ` +
    `record that CONTRADICTS a premise asserted in the subject brief below — the brief is written by a ` +
    `human or agent who may be wrong, and catching that here is far cheaper than after three lenses have ` +
    `built on it.\n\nSubject:\n${subject}`,
  { agentType: 'general-purpose', label: 'orient', phase: 'Orient', schema: ORIENT_SCHEMA },
)

const RECORD = orient
  ? `\n\nRECORD (Phase 0 — what this repo already knows; argue AGAINST it, do not rediscover it. Anything ` +
    `under \`rejected_fixes\` must NOT be re-proposed, and \`contradicts_subject\` flags premises in the ` +
    `subject that the record disputes):\n${JSON.stringify(orient, null, 2)}`
  : `\n\nRECORD: Phase 0 returned nothing — proceed WITHOUT it, and treat every "already known" claim as ` +
    `unestablished rather than assuming the record agrees with you.`

// ---- Phase 1: the DETERMINISTIC lens, then R-DIAGNOSIS ----
// engine/diagnostics.py is mechanical: it compares the case's contract_claim to the SUT's BUSINESS_RULES
// and the runtime response. Never LLM what a rule can decide — so it runs FIRST when a pack is named, and
// its verdict is handed to R-DIAGNOSIS as evidence, not as an override.
phase('Diagnose')
const diagnostics = PACK
  ? await agent(
      `MECHANICAL step — run one command and report its output. Do NOT analyse, diagnose or fix anything.\n` +
        `1. Run: \`python3 -m engine.diagnose --sut ${SUT} --pack ${PACK}${SEED_BUG ? ' --seed-bug' : ''}\`\n` +
        `2. Then run: \`echo "EXIT=$?"\`\n` +
        `3. Report \`verdict\` (the verdict word it printed), \`rule\` (the contract rule id it resolved, or ` +
        `"" if none), \`exit_code\`, and \`raw\` = the full stdout+stderr VERBATIM.\n` +
        `If the command fails to run at all, report verdict "COMMAND-FAILED" and put the error in \`raw\`.`,
      { label: 'engine.diagnostics', phase: 'Diagnose', schema: DIAGNOSTICS_SCHEMA },
    )
  : null

const DIAGNOSTICS_NOTE = diagnostics
  ? `\n\nDETERMINISTIC LENS (engine/diagnostics.py — mechanical, contract_claim vs BUSINESS_RULES vs the ` +
    `runtime response). Its verdict is EVIDENCE, not an override; where you disagree, say so and cite ` +
    `why:\n${JSON.stringify(diagnostics, null, 2)}`
  : `\n\nDETERMINISTIC LENS: not run (no \`pack\` in the subject), so there is no mechanical verdict to ` +
    `weigh — do not assume one.`

const diag = await agent(
  `Diagnose this failing/changed Qensei case BEFORE any fix, for SUT \`${SUT}\`.\n\n` +
    `FIRST run the SUT-source freshness self-gate: \`python3 -m engine.freshness_gate --sut ${SUT}\`. It is ` +
    `a no-op for an in_process mock and for a sourceless SUT; if it reports STALE/DIRTY for a remote SUT, ` +
    `return verdict UNDOCUMENTED-ESCALATE with source_stale=true and do NOT diagnose against an old ` +
    `clone.\n\nSubject:\n${subject}${RECORD}${DIAGNOSTICS_NOTE}\n\n` +
    `Return your structured verdict, citing a \`sut/<name>/source/<file>:<line>\` (or, for a sourceless ` +
    `SUT, a ticket/doc anchor) for every claim about the system. Set needs_mechanism=true ONLY if the ` +
    `failure turns on SUT mechanism (timing / scheduling / run-eligibility / coalescing / component state) ` +
    `— a UI route or selector drift is a TEST_BUG, not mechanism. Set needs_evidence=true if there are ` +
    `claims, raw gate/CI state, or cross-test / durable-collision / env-divergence concerns to verify.`,
  { agentType: 'r-diagnosis', label: 'r-diagnosis', phase: 'Diagnose', schema: DIAG_SCHEMA },
)

if (!diag) {
  return {
    decision: 'ESCALATE',
    digest: 'R-DIAGNOSIS returned nothing — escalate to the human. The panel cannot adjudicate a failure it never diagnosed.',
    record: orient,
    diagnostics,
  }
}
if (diag.source_stale) {
  return {
    decision: 'ESCALATE',
    digest:
      `The SUT source for ${SUT} is stale — run \`make sync-source SUT=${SUT}\` and re-run the panel. ` +
      'A citation against a stale clone is worse than none (R-DIAGNOSIS freshness self-gate).',
    record: orient,
    diagnostics,
    diagnosis: diag,
  }
}

// ---- Phase 2: Triage — conditional, parallel ----
// Sequential-then-conditional on purpose: R-DIAGNOSIS's flags DECIDE whether these run at all. Running
// them eagerly would spend two agents to save one agent's latency, on a failure not yet understood.
phase('Triage')
const lensThunks = []
if (diag.needs_evidence) {
  lensThunks.push(() =>
    agent(
      `Verify the claims / raw gate state / cross-test impact for this Qensei failure on SUT \`${SUT}\`. ` +
        `The green dot is not evidence — pull the raw state yourself (re-run the gate or read the CI job ` +
        `log, do not trust a summary).\n\nSubject:\n${subject}${RECORD}\n\n` +
        `Diagnosis:\n${JSON.stringify(diag, null, 2)}\n\n` +
        `Return structured findings: cite or reject each claim, and flag cross-test / durable-collision / ` +
        `env-divergence impact. Every citation must be a real \`sut/<name>/...:<line>\` that resolves.`,
      { agentType: 'r-evidence', label: 'r-evidence', phase: 'Triage', schema: EVIDENCE_SCHEMA },
    ).then((r) => (r ? { lens: 'r-evidence', findings: r } : null)),
  )
}
if (diag.needs_mechanism) {
  lensThunks.push(() =>
    agent(
      `Verify the SUT-mechanism reasoning behind this failure on SUT \`${SUT}\`. Run ` +
        `\`python3 -m engine.freshness_gate --sut ${SUT}\` first and report it verbatim. Require ` +
        `\`sut/<name>/source/<file>:<line>\` citations (or ticket/doc anchors for a sourceless SUT), and ` +
        `SURFACE every mechanism call even where you agree — that is the class the panel cannot close ` +
        `alone.\n\nSubject:\n${subject}${RECORD}\n\nDiagnosis:\n${JSON.stringify(diag, null, 2)}\n\n` +
        `Return structured findings (CITED / UNCITED / MISREAD per claim).`,
      { agentType: 'r-mechanism', label: 'r-mechanism', phase: 'Triage', schema: MECHANISM_SCHEMA },
    ).then((r) => (r ? { lens: 'r-mechanism', findings: r } : null)),
  )
}
if (lensThunks.length === 0) log('no Tier-2 flags set — skipping R-EVIDENCE / R-MECHANISM')
const lenses = (await parallel(lensThunks)).filter(Boolean)

// ---- Citation gate: the deterministic forcing function, BEFORE the JUDGE ----
// Run the anti-fabrication gate over every citation the lenses emitted, as its own step — not left to the
// JUDGE remembering a prose instruction (a policy without a gate is not followed; this mirrors
// R-DIAGNOSIS's freshness self-gate). The JS sandbox has no shell, so a single-purpose step-agent runs
// `python3 -m engine.citation_gate` and the script injects the structured result into adjudication.
phase('Adjudicate')
const findingsForGate = JSON.stringify({ diagnostics, diagnosis: diag, lenses })
const citationGate = await agent(
  `MECHANICAL step — run the citation gate. Do NOT analyse, diagnose or fix anything.\n` +
    `1. Create a temp file with \`mktemp /tmp/qensei-panel-cite.XXXXXX\`.\n` +
    `2. Write the EXACT findings JSON below into that file (use the Write tool).\n` +
    `3. Run \`python3 -m engine.citation_gate <tempfile>\` then \`echo "EXIT=$?"\`.\n` +
    `4. Report: \`exit_code\`; \`fabricated\` = the citation strings it reported as MISSING-FILE / ` +
    `LINE-OUT-OF-RANGE; \`unverifiable\` = those reported as missing source; \`raw\` = its output verbatim.\n` +
    `Exit 0 = every citation resolves (or none were emitted); 1 = FABRICATED; 3 = UNVERIFIABLE.\n\n` +
    `Findings JSON:\n${findingsForGate}`,
  { label: 'engine.citation_gate', phase: 'Adjudicate', schema: CITATION_GATE_SCHEMA },
)

// ---- Phase 3: JUDGE ----
const judgeInput = JSON.stringify(
  { record: orient, deterministic_lens: diagnostics, diagnosis: diag, lenses, citation_gate: citationGate },
  null,
  2,
)
const verdict = await agent(
  `Adjudicate the Qensei review panel for this failure on SUT \`${SUT}\`. Decide per finding ` +
    `(BLOCK / FIX / FLAG / ESCALATE), apply the rebuttal + loop rules (2x the same finding with the same ` +
    `class of rebuttal -> STOP and escalate). On a REAL_BUG, assemble a structured bug report for the ` +
    `HUMAN to file via the ticket provider — you never open the ticket yourself. Surface every ` +
    `SUT-mechanism call. No auto-merge on all-PASS: passing the panel means the floor was raised, not that ` +
    `the human is done.\n\n` +
    `The \`citation_gate\` result is the deterministic anti-fabrication gate over every citation the lenses ` +
    `emitted: a claim resting on a \`fabricated\` citation (exit 1) MUST NOT clear regardless of cross-lens ` +
    `consensus — drop it or send it back to re-read the FRESH source; an \`unverifiable\` citation (exit 3, ` +
    `the owning source not fetched) is NOT fabrication — require it fetched and re-cited, or route it as a ` +
    `labelled hypothesis, never clear it as fact. **Echo the gate's \`raw\` output in your digest as proof ` +
    `it ran** — do not merely assert that it did.\n\n` +
    `Where the deterministic lens (engine/diagnostics.py) and R-DIAGNOSIS disagree, surface BOTH: the ` +
    `mechanical verdict is evidence, not an override. Never weaken an acceptance criterion to clear a ` +
    `finding.\n\n` +
    `Produce a decision-grade escalation digest (what is blocked, 2-3 options with pros/cons, the evidence, ` +
    `one clear ask) if the human is needed; otherwise a short "panel clear — floor raised on: ..." ` +
    `summary.\n\nRecord + verdicts + findings + citation gate:\n${judgeInput}`,
  { agentType: 'judge', label: 'judge', phase: 'Adjudicate', schema: VERDICT_SCHEMA },
)

return {
  decision: verdict?.decision ?? 'ESCALATE',
  digest: verdict?.digest ?? 'JUDGE returned nothing — escalate to the human.',
  record: orient,
  diagnostics,
  diagnosis: diag,
  lenses,
  citation_gate: citationGate,
  verdict,
}
