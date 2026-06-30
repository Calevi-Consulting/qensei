#!/usr/bin/env bash
# Dev-environment setup for qa-framework.
#
# The framework RUNTIME is zero-dependency: `python3 -m engine.run --sut <site>` (and the
# whole `make demo` / `make test` flow) works with no install at all. This script installs
# only the DEV / TEST toolchain — pytest, pytest-xdist, ruff (lint), pip-audit (CVE scan) —
# via Poetry into a project-local ./.venv. Run it with `make install`.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v poetry >/dev/null 2>&1; then
  cat >&2 <<'EOF'
  Poetry is not installed — it manages this project's dev/test dependencies.
  Install it first, then re-run `make install`:

    pipx install poetry                                   # recommended (isolated)
    # or the official installer:
    curl -sSL https://install.python-poetry.org | python3 -
    # or, quick-and-dirty:
    python3 -m pip install --user poetry
EOF
  exit 1
fi

echo "==> poetry install (pytest, pytest-xdist, ruff, pip-audit, playwright -> ./.venv)"
poetry install

echo "==> playwright install chromium (the browser the UI lane drives; ~150MB)"
poetry run playwright install chromium

cat <<'EOF'
==> dev toolchain ready. Common commands:
      make pytest    # REST + unit tests in parallel (pytest -n auto)
      make test-ui   # browser (Playwright) UI packs, headless
      make ui-watch  # watch the UI verification live (headed, slowed-down)
      make lint      # ruff lint
      make cve       # pip-audit dependency CVE scan
      make verify    # lint + cve + pytest + the offline gates
    (or run any of them directly with `poetry run <tool>`)
EOF
