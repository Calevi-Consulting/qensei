# Security Review Policy

A mandatory, non-skippable review pass run on every change that touches code. It has two parts:

1. **Dependency CVE scanning** — tool-verified, runs a scanner against the project's dependency manifest.
2. **OWASP Top 10 review** — an AI-assisted, best-effort read of the changed code for common vulnerability patterns.

This policy applies to a QA / test-automation framework just as it does to any product code: the harness, fixtures, helpers, page objects, and CLI tooling are real code, they hold credentials to the system under test, and their dependencies are an attack surface. Review them.

> **Scope and limitations**: The OWASP portion is an AI-assisted best-effort pass — a workflow aid, not a substitute for approved security scanners, penetration testing, or formal audit. AI can miss vulnerabilities, apply checks inconsistently, or produce false confidence. Findings do **not** constitute evidence of any regulatory or compliance standard (e.g. SOC 2, PCI-DSS, HIPAA). Organizations with compliance requirements must use approved, auditable tooling for that purpose. "An AI reviewed it" is not evidence of meeting any security standard.

---

## Part 1 — Dependency CVE Scanning (mandatory, tool-verified)

Run a dependency vulnerability scanner against the changed code's dependency manifest. This part is **non-negotiable** and **non-skippable** — it runs on every code change regardless of any project-level relaxation of validation reports or other quality gates.

- Pick the scanner that matches the project's ecosystem:
  - Python → `pip-audit` (or `safety`)
  - Node / JavaScript → `npm audit` (or `pnpm audit` / `yarn audit`)
  - Rust → `cargo audit`
  - Go → `govulncheck`
  - (others) → the ecosystem's standard vulnerability scanner
- **Record the tool name and version** in the review output. A scan with no recorded tool/version does not count as a scan.
- Triage every reported advisory:
  - **Fixable** (a patched version exists) → bump the dependency and re-run the test suite.
  - **No fix available** → document the advisory ID, affected component, and why it is or is not exploitable in this project's usage. Decide explicitly whether to proceed.
  - **False positive / not reachable** → note why, with the advisory ID, so the next reviewer does not re-litigate it.
- **If the scanner is not installed**: do not silently skip. Ask before installing (installation is environment-specific). If installation is declined, **explicitly record that CVE scanning could not be completed** and what was therefore not verified — never report a clean scan that did not run.

Pin and review transitive dependencies the same way: a vulnerability three levels deep in a lockfile is still in your build.

---

## Part 2 — OWASP Top 10 Review (AI-assisted, best-effort)

Read the changed code for common vulnerability patterns. A developer aid to catch obvious issues early — it does not replace SAST/DAST tooling or formal review.

### Checklist

1. **Injection** — SQL, command, and code injection
   - Prefer parameterized queries over string concatenation
   - Flag `eval()`, `exec()`, and `subprocess(..., shell=True)`
   - Validate/sanitize external input at system boundaries (e.g. responses from the system under test, fixture inputs, environment-supplied values)
2. **Broken authentication** — credential handling in changed code
   - No hardcoded passwords / API keys / tokens (use a secrets manager or environment-injected config)
   - Secure session/token handling; do not persist live tokens to disk or fixtures
   - Proper password hashing (bcrypt, argon2) where the project stores any
3. **Sensitive data exposure** — data-leakage paths
   - No credentials, tokens, or PII in logs, assertion messages, or error output (mask them)
   - No secrets committed to version control (config files, fixtures, recorded HTTP cassettes, screenshots, test artifacts)
4. **XML external entities (XXE)** — flag external-entity processing in XML parsers if present
5. **Broken access control** — authorization logic in changed code
   - Verify permissions are checked before privileged operations
6. **Security misconfiguration** — insecure defaults
   - Debug mode left on, default credentials, disabled TLS verification, missing security headers
7. **Cross-site scripting (XSS)** — in any web/HTML-rendering context
   - Escape HTML/JavaScript in user- or test-generated content
8. **Insecure deserialization** — deserializing untrusted data
   - Prefer safe formats (JSON over `pickle` / native object deserialization)
9. **Components with known vulnerabilities** — covered by **Part 1** (dependency CVE scanning)
10. **Insufficient logging & monitoring** — security-relevant events are recorded
    - Authentication failures, access-control violations
    - …without leaking sensitive data into the log output

### Code security anti-patterns

- **Hardcoded secrets** — API keys, passwords, tokens in source, fixtures, or test data
- **Unsafe file operations** — path traversal, insecure temp-file usage (use the project's scratch/temp conventions)
- **Insufficient input validation** — missing sanitization at system boundaries
- **Race conditions** — TOCTOU (time-of-check / time-of-use) patterns
- **Insecure randomness** — `random` instead of `secrets` for security-sensitive values
- **Disabled transport security** — `verify=False`, ignored certificate errors, or downgraded TLS, even "just for tests"

---

## Remediation

- **Minor issues** → fix directly and re-run the test suite.
- **Major issues** requiring refactoring → loop back to the refactor / code-quality pass, then fix.
- **Critical vulnerabilities** → stop and fix immediately before proceeding.
- After any **significant security fix** → re-run the full validation suite.

## Guidelines

- Prioritize fixes: **Critical > High > Medium > Low**.
- Document security decisions and trade-offs (especially accepted, unfixed advisories).
- When in doubt about a potential vulnerability, err on the side of caution.
- Commit security fixes separately with clear messages (e.g. `security: fix command injection in fixture loader`).
- **Do not claim compliance** — this review may catch issues, but it is not evidence of meeting any security standard.
