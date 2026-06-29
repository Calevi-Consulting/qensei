# Writing and Communication Standards

All written artifacts (specs, test-design docs, documentation, commit messages, validation reports, diagnostic reports, code comments) should prioritize clarity and precision over style.

## Generation-Time Checklist

Apply these while drafting, not only on review. Each is a lexical or behavioral choice made as the sentence is written, so first-draft compliance is the target rather than a later cleanup. The detailed rationale for each rule lives in the sections below; this is the at-write digest.

Most of this policy is enforceable at generation time. Only the short residue at the end needs the finished artifact to check.

**While writing any durable artifact:**

- Use the plain word, not the inflated default: "use" not "leverage", "important" not "crucial", "before" not "prior to". (AI vocabulary, academic tells.)
- Write the verb directly: "the scanner reports X", not "the scanner serves as a safeguard for X". (Copula and inflated framing.)
- State Y directly; skip the "not X, it's Y" inversion. (Negative parallelisms.)
- No superlatives or marketing claims; quantify instead — "1000 req/sec", not "highly performant".
- Open on the content. No "Great question", "Certainly", "I hope this helps", no knowledge-cutoff disclaimer, no "In summary" recap. (Sycophantic openers.)
- Third person and passive by default in durable docs; no "I" / "we". (Voice and Pronoun Use.)
- Choose the punctuation as you write: colon to define or introduce, period or semicolon to join clauses, em-dash only for a parenthetical aside or an end-of-sentence kicker. Do not default to the em-dash. (Em-dashes.)
- Quote sources verbatim — error messages, log lines, config values exactly; bracket any alteration. (Quote accuracy.)
- Never invent an attribution, a scenario, or a date. If a position is inferred, mark it as an assumption; if an incident is hypothetical, label it. (Fabrication and Attribution Integrity.)
- Before writing a negative-existence claim ("no newer X", "not in the repo"), run the one-command lookup. Mark unverified claims uncertain as you write them, not after. (Evidence and Uncertainty Disclosure.)
- Name the section's subject in the heading; no narrative, clickbait, or vague-abstraction headings. (Headings.)
- Ground each hedge in its reason; do not blanket-qualify established facts. (Hedging calibration.)
- Lead the section with the verdict when you already know it. (BLUF.)
- Frame the situation and complication as you write an introduction. (SCQA.)
- Do not pad a list to three; use the number of items that belong. (Rule-of-three lists.)

**Revision-pass residue** — the only checks that need the finished artifact, because they are properties of the whole rather than of any one sentence:

- **MECE**: re-read the full criteria or step list once for overlap and gaps. Independence and completeness cannot be checked until every item exists.
- **Sentence and paragraph burstiness**: scan the finished section for runs of same-length sentences or uniform paragraph sizes. Variance is a whole-section property.
- **Hedging density**: count hedges per paragraph (ceiling about three). A defensible per-sentence hedge can still aggregate into over-hedging across a paragraph.
- **BLUF when the conclusion emerged late**: if the analysis was written before the answer was known, move the verdict to the front on review.

This residue is bounded and single-pass. Everything above it is generation-time; reaching the residue should be a quick scan, not a rewrite. The rhythmic items here (burstiness, hedging density) are the deeply-trained patterns where first-draft compliance is partial even with priming; the scan is their safety net.

## Language Patterns to Avoid

Inflated, generic, or AI-default language obscures meaning without adding information. The patterns below cluster into three overlapping families: marketing/superlative language, AI-voice tells, and habitual filler. Apply them while drafting (the Generation-Time Checklist above is the at-write digest); the entries below carry the rationale and worked examples for each.

**Superlatives and marketing fluff**:

- Superlatives: "amazing", "awesome", "excellent", "incredible", "fantastic"
- Marketing claims: "enterprise-grade", "world-class", "cutting-edge", "next-generation", "industry-leading"
- Vague quality claims: "robust", "scalable", "performant", "reliable" (unless backed by metrics)

Replace with concrete, quantified descriptions: "Handles 1000 req/sec" not "highly performant"; "Reduces load time from 3s to 800ms" not "dramatically faster".

**Em-dashes**: Match the punctuation to the job. Em-dashes earn their keep for parenthetical asides that break sentence flow and for kicker clauses where rhythm matters; they become a tell when they do work a colon or period would do without drama.

| Use | Punctuation |
| --- | --- |
| Defining a term (`Term: meaning`) | colon |
| Introducing a list | colon |
| Equivalence, "i.e.", "namely" | colon |
| Joining two complete clauses where the second elaborates the first | period or semicolon |
| Parenthetical aside that breaks sentence flow | em-dash or parentheses |
| Kicker or rhetorical surprise at sentence end | em-dash |

AI-authored prose tends to default to em-dashes across all six rows. On revision, scan em-dashes and ask which row each one fits; if the answer isn't "parenthetical aside" or "kicker", another mark is doing the job better.

**Negative parallelisms**: "It's not X, it's Y" / "not just X but Y" / "more than just X". State Y directly without the inverted setup.

**Rule-of-three lists**: Three-item lists used for rhythm rather than enumeration. If only two items belong, use two; if four, use four. Do not pad to three.

**AI vocabulary**: Replace with plain alternatives.

| Avoid | Use Instead |
|-------|-------------|
| crucial, pivotal, vital | important, required, or specify what depends on it |
| landscape, ecosystem, realm | name the actual system or domain |
| interplay | interaction; how X affects Y |
| delve, navigate, harness, leverage | use, handle, search, work with |
| underscore, illuminate, highlight | show, point out |
| tapestry, beacon, fabric | (cut entirely) |
| prior to, subsequent to | before, after |
| in light of, with respect to, in terms of | because of, about, for |
| shed light on, pave the way for | clarify, enable |
| a myriad of, a plethora of, paramount | many, several, essential |
| the fact that | (rewrite the sentence) |

**Overused technical phrases**: These have legitimate technical uses but turn into filler when overused. Use sparingly and only with a concrete referent.

- `load-bearing`: fine for "this assumption is load-bearing for the proof"; not fine as generic emphasis
- `shape`: fine for "shape the records into a TSV row"; not fine for "shape the design" or "shape decisions"
- `drift`: fine for "config drift", "schema drift"; not fine as a generic decay metaphor

**Copula and inflated framing**: Replace "serves as", "stands as", "plays a key role in", "acts as" with the direct verb. "The CVE scanner reports vulnerable dependencies" not "The CVE scanner serves as a critical safeguard against dependency risks".

**Sycophantic openers and chatbot artifacts**: Cut "Great question", "I hope this helps", "Certainly!", "Of course!", knowledge-cutoff disclaimers, and editorial recap closings ("In summary, we have...").

**Excessive emphasis**: Boldface inside flowing prose, Title-Cased Section Headings, and emoji bullets. One bolded lead per logical group at most.

**Headings**: A heading names what the section contains; it does not tease or dramatize it. This extends the casing rule above to heading content. Avoid narrative framing ("The Hidden Cost of Serialization"), clickbait ("Why Rebuilds Destroy Everything"), and vague analytical abstractions ("Broader implications", "Wider context", "Industry-wide impact"). Name the subject, not the abstraction: "Parity overwrite on degraded RAID arrays", not "The Silent Killer". Self-check: a heading that would work as a thriller chapter title or a video thumbnail gets rewritten.

**Scare quotes**: Quotation marks are for actual quotations from a named source, not for flagging a normal word as suspect or ironic. `the "improved" path` and "the so-called fix" editorialize without adding information; state the objection directly or drop the quotes.

**Performative urgency**: "Act now", "critical to address immediately", and similar urgency need a concrete consequence in the same sentence — a real deadline, a measured cost, a named failure mode — or they get cut. "Fix before the 2026-07-01 cert expiry" earns the urgency; "this is urgent" does not.

**Hallucinated markup artifacts**: The strings `oaicite`, `contentReference`, `turn0search0`, `grok_card`, and `attributableIndex` are chatbot citation placeholders. Any occurrence in a committed artifact means text was pasted from an AI tool unedited. Zero tolerance; grep for them before commit.

**Examples**:

| Avoid | Use Instead |
|-------|-------------|
| "This amazing feature provides enterprise-grade scalability" | "This feature supports horizontal scaling via Redis clustering" |
| "Incredible test coverage improvements" | "Increase test coverage from 45% to 87%" |
| "Cutting-edge AI-powered optimization" | "Use TF-IDF vectorization for document similarity" |
| "The interplay between auth and rate-limiting is crucial — not optional but central" | "The auth layer enforces per-user rate limits before the request reaches the handler" |
| "The CVE scanner serves as a critical safeguard, helping to illuminate dependency risks" | "The CVE scanner reports vulnerable dependencies" |
| "We need to navigate the complex landscape of testing strategies" | "Pick a test level: unit if the function is pure, integration if it crosses a boundary" |
| "This is a load-bearing decision that will shape the trajectory of the project" | "This decision is hard to reverse later because the dual-write path cannot be removed without a backfill" |

**Applying these lists without over-correcting**: The banned-word lists are heuristics, not a linter. Three guards keep them from damaging correct prose:

- **Exclusion zones**: never flag text inside direct quotes, proper names, error messages, ticket titles, code, or config. A log line that contains "leverage" is data, not your prose.
- **Context-aware severity**: a banned word next to a specific entity (a statute number, a date, a dollar amount, a service name) is usually carrying technical meaning, not filler. "comprehensive audit by the regulator in 2024" is fine; "a comprehensive examination of the issues" is not.
- **Literal vs metaphorical**: flag the metaphor, keep the literal use. "the vendor's software ecosystem" (literal product term) stays; "the repair ecosystem" (metaphor) goes. The same split applies to landscape, navigate, fabric, and beacon.

The lists exist to catch language that adds no information. When the word is doing real work, leave it.

**Purpose**: Written artifacts exist to communicate test status, requirements, and technical decisions clearly. Inflated, generic, or AI-default language adds no information and obscures meaning.

## Voice and Pronoun Use

Durable documents describe the system under test and the work, not the author's process. Avoid first-person pronouns ("I", "we", "my", "our") in specs, validation reports, open-questions sections, design docs, and commit/PR descriptions. Neutral third-person or passive voice reads better across handoffs and does not bias toward whoever wrote the doc.

**Passive voice is the intended default for technical artifacts.** This policy targets specs, validation reports, and design docs where the system (not the author) is the actor. Constructions like "the migration is applied" or "the path was not tested" support that framing. Active voice is welcome for variation when a specific actor matters; treat passive as the working default rather than something to fix. Generic "avoid passive voice" advice from style guides does not apply here.

**Examples**:

| Avoid | Use Instead |
|-------|-------------|
| "I did not test this path" | "This path was not tested" / "Not verified" |
| "I observed X on 2026-04-21" | "Observed X on 2026-04-21" |
| "We should confirm Y" | "Y should be confirmed" / "To confirm: Y" |
| "I think this is correct but..." | Remove the hedge; if uncertain, mark explicitly as uncertainty (see below) |

**Scope**: specs, validation reports, PR/commit descriptions, design docs, and inline code comments that will be read by future maintainers. Does not apply to conversational chat, session status updates, or tool-call narration.

## Structural Rules (BLUF, MECE, SCQA)

Three rules drawn from Barbara Minto's Pyramid Principle. They address structural failure modes that the word-level rules above do not catch.

**Scope**: specs, validation reports, PR/MR descriptions, commit message bodies, design docs, ADRs, runbooks, and other durable artifacts that humans will read after the originating session. Does **not** apply to conversational chat, session status updates, tool-call narration, or live design discussion where surfacing tradeoffs before a recommendation is the point.

**Application**: BLUF and SCQA are generation-time — lead with the verdict when it is known, and frame the situation and complication as the introduction is written. MECE is the one structural rule that needs the finished artifact: independence and completeness cannot be checked until every list item exists, so it stays a single revision-pass scan (see the Generation-Time Checklist's residue). Reaching that scan should be a quick read, not a rewrite.

### BLUF — bottom-line up front

Lead with the conclusion, then the supporting evidence. The first sentence of a section should be the answer, not the methodology that produced it. AI tends to bury verdicts under "Ran X, then Y, considered Z, and found that..." — flip it.

| Avoid | Use Instead |
|-------|-------------|
| "After running the suite, reviewing the new test cases against the spec, and checking for any flaky behavior over three runs, the test suite is green" | "Test suite green. Run 3x, no flakes; new cases match spec acceptance criteria 1–4." |
| "The change adds a feature flag, wires it through the checkout path, updates the migration to backfill from the legacy column, and includes integration tests" | "Adds a feature flag for the new checkout path. Migration backfills from the legacy column; integration tests included." |

A skimming reviewer should get the answer in the first sentence. Burying the verdict makes triage harder and trains readers to skip to the end.

**Conflict with the Voice section**: BLUF can read as blunt — "Test suite green" is a fragment. That is intentional and overrides the first-person and passive-voice softening from the Voice section. The opening sentence of a section is allowed to be a fragment when it is the verdict.

### MECE — mutually exclusive, collectively exhaustive checklists

Spec acceptance criteria, validation phase items, and any list of conditions or steps should be:

- **Mutually exclusive**: no two items overlap. If criterion 1 says "the migration runs cleanly" and criterion 2 says "rollout completes without errors", merge them or sharpen the distinction.
- **Collectively exhaustive**: cover the full surface area. If a feature has three failure modes, all three need a check; missing one leaves a silent gap.

Overlapping checklists produce ambiguous done-states (is criterion 1 *or* criterion 2 enough?) and waste review time. Gap-having checklists let bugs ship behind a green check. Both are common AI failure modes — the model produces three plausible-looking items without verifying they are independent or complete.

**Revision prompt**: "For each pair of items, do they overlap? For the full set, what is missing?"

### SCQA — situation, complication, question, answer for introductions

Specs, ADRs, and root-cause / diagnostic reports benefit from explicit context framing before the requirements or findings:

- **Situation**: the existing state — what is currently true.
- **Complication**: what changed or what is broken — the reason this artifact exists.
- **Question**: the implicit question the artifact answers. Often unstated; surfacing it sharpens the answer.
- **Answer**: the requirements, decision, or resolution.

A spec that opens with a requirements list without framing the complication is harder to evaluate later — readers cannot tell whether the requirements still address the original motivation or whether scope drifted. SCQA forces the framing to be explicit and durable.

**Example**:

```markdown
## Background
The login regression pack exercises the password-auth flow only.                   (Situation)
SSO login shipped in the 2026-Q1 release; the pack has no SSO coverage,
and an SSO regression reached production undetected.                               (Complication)
Which SSO paths must the pack cover to catch that class of regression?            (Question)

## Requirements
... (Answer)
```

## Evidence and Uncertainty Disclosure

Every factual assertion in a durable document should be backed by one of:

- a direct observation recorded in this session (with command, output, or date)
- a prior verified claim referenced by file/line, URL, or issue ID
- an explicit "not verified" / "to confirm" flag

Guessing dressed up as fact is the worst of both worlds — it looks authoritative but is unreliable, and the error is invisible to readers who trust the doc. When no ready path to verification exists in the current session, mark the claim as uncertainty rather than write it as fact.

**Commonly-leaked unverified claims** (watch for these):

- **Environmental / operational**: "seed job X populates table Y", "flag Z enables W", "the staging environment has data for Q"
- **Cross-service behavior**: "data flows from service A to B through topic T"
- **Migration / deployment behavior**: "this rollout is zero-downtime", "the column is backfilled on write"
- **Historical bug-status**: "that was fixed in 2026.01", "that regression was resolved"
- **Framework / library behavior**: "the ORM emits a hash semijoin here" (unless an `EXPLAIN` was actually run)
- **Negative-existence claims**: "no newer X is available", "this can't be fixed", "the package doesn't exist", "this never worked", "there's no upstream resolution", "not in the repo". These are a high-risk pattern — easy to slip in as throwaway justification for choosing approach Y, hard to disprove without enumeration, and almost always written as inference from a proximate observation ("X didn't get installed automatically" → "X must not exist") rather than an actual lookup. The verification cost is almost always tiny: one shell command (`apk policy`, `pip index versions`, `apt-cache madison`, `cargo search`, `gh search`, `nm -D`, `git log -p -S`, `git tag --contains`). Run the lookup before writing the negative claim. If the lookup confirms the negative, cite the command and its output. If you cannot run the lookup, mark the claim as **unverified inference** with the verification step that would resolve it, rather than asserting the negative as fact.

**Pattern for uncertainty disclosure**:

```markdown
**Not verified** (what wasn't checked, and why):
- Whether the nightly seed job populates the `user_entitlements` table.
  That path was not exercised; only the post-seed state was inspected.
- Whether the entitlement data is expected to flow through the seed job at all,
  or is loaded by a separate import step.
```

**Bias**: when in doubt between omitting a claim and marking it uncertain, mark it uncertain — the next reader benefits from knowing the gap exists.

**Hedging calibration**: Uncertainty disclosure is not license to blanket-hedge. Two failure modes sit on opposite sides of the same line. Under-disclosure writes a guess as fact. Over-hedging sprays "may", "might", "could", "generally", "it seems" across established facts, which reads as AI default and buries the one hedge that matters. Ground each hedge in its specific reason ("not verified — that seed path was not exercised") rather than qualifying everything ("this might generally tend to populate the table"). Rough ceiling: more than three hedges in a paragraph, or a hedge on a fact you actually observed this session, is over-hedging. Facts you verified get stated flat.

**Disclosure block vs flowing prose**: The "not verified" discipline belongs in a designated uncertainty block, not sprinkled through the narrative. In the flowing prose of a spec or report, do not narrate your own search process — "could not be located", "no record was found", "as of [date] this could not be found" add no durable information and read as filler. State what you can support; route what you cannot into the explicit uncertainty block. The gap gets recorded once, in the place a reader looks for it.

**Companion rule**: this section is the authoring-side default for writing durable docs. If the project defines a separate prompt-hygiene policy (covering the user side — what to ask for in prompts), apply both. This evidence discipline applies to specs, validation reports, and diagnostic reports on its own, regardless of whether any prompt-hygiene rule is in play.

## Fabrication and Attribution Integrity

Evidence discipline (above) governs claims you are unsure of. This section governs claims you must never invent at all, even to fill a gap. The failure mode is different: an unverified claim marked uncertain is honest; a fabricated one is not, and some fabrications carry legal risk.

**No fabricated attributions.** Do not put a position, quote, or decision in a named person's, team's, or company's mouth from inference. "QA flagged this as a regression", "the platform team decided X", "the customer reported Y" must trace to a real message, ticket, transcript, or commit — cite it. Inferring someone's position from their role ("the security team would object to this") is not attribution; if you need their position, ask, or mark it as your own assumption. Outside the codebase a fabricated attribution is a defamation risk; inside it, the fabrication sends the next maintainer to the wrong person.

**No fabricated scenarios.** Do not write a narrative incident — a hypothetical outage, a user complaint, an example failure — as though it were a real, documented event. Label hypotheticals as hypothetical ("if the token expires mid-write, ..."). A real incident gets a link to the ticket or postmortem.

**No fabricated dates or milestones.** Do not invent dates for releases, fixes, deployments, or regressions. "Fixed in 2026.01" and "regressed after the April migration" are factual claims about history; cite the commit, tag, or ticket, or do not write the date. This is stronger than the negative-existence and historical-bug-status items in Evidence above — there the rule is "verify before asserting"; here it is "never invent".

**Quote accuracy.** When you put text in quotation marks and attribute it, every word matches the source. Do not silently correct grammar, swap a pronoun, or clean up an error message; a misquoted error string or stack trace is a correctness bug in a spec, not a style choice. If you must alter a quote for clarity, mark the change with square brackets. If the wording is awkward, paraphrase without quotation marks instead. Quote error messages, log lines, and config values verbatim — these are the cases where exactness is load-bearing.

**Scope**: specs, validation reports, diagnostic reports, PR/commit descriptions, design docs, and any artifact that names a person, team, system, date, or incident. Conversational chat and live design discussion are exempt from the prose-style rules but not from the no-fabrication rule — do not invent an attribution in chat either.
