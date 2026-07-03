# Security Policy

## Reporting a vulnerability

Please do **not** open a public issue for security vulnerabilities.

Report privately through GitHub's **"Report a vulnerability"** button on the
repository's [Security tab](https://github.com/Calevi-Consulting/qensei/security/advisories/new).
This opens a private advisory visible only to the maintainers.

Include, where possible:

- A description of the vulnerability and its impact.
- Steps to reproduce (a minimal case or a failing regression pack is ideal).
- Affected version / commit, and the affected SUT plugin if applicable.

You can expect an initial acknowledgement within a few days. Once a fix is ready,
a coordinated disclosure will be arranged.

## Scope

Qensei's runtime is zero-dependency (Python 3 standard library); the dev/test
toolchain is Poetry-managed and scanned with `pip-audit` (`make cve`). Reports
about either the framework itself or its declared dependencies are in scope.

Credentials and per-developer targets are never committed — they resolve at
runtime from `QAF_*` environment variables / `.env` (see `engine/config.py`). If
you find a hardcoded secret in the history, treat it as a vulnerability and report
it privately.
