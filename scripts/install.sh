#!/usr/bin/env bash
# Dev-environment setup for Qensei.
#
# The framework RUNTIME is zero-dependency: `python3 -m engine.run --sut <site>` (and the
# whole `make demo` / `make test` flow) works with no install at all. This script installs
# only the DEV / TEST toolchain — pytest, pytest-xdist, ruff (lint), pip-audit (CVE scan) —
# via Poetry into a project-local ./.venv. Run it with `make install`.
#
# It is SELF-BOOTSTRAPPING: if Poetry, or the Python version the project targets, is
# missing, it provisions them itself. Everything it provisions lands in ./.tooling/
# (gitignored) — project-local, no sudo, nothing written outside the repo, no shell
# profile touched. `rm -rf .tooling` reverts the bootstrap completely.
#
# Escape hatch: QENSEI_NO_BOOTSTRAP=1 disables provisioning; the script then reports what
# is missing and how to install it by hand (the pre-bootstrap behaviour).
set -euo pipefail
cd "$(dirname "$0")/.."

TOOLING="$PWD/.tooling"
TOOLING_BIN="$TOOLING/bin"

# The Python the project targets, read from pyproject's `python = "^3.14"` so the two
# cannot drift. Caret semantics: >= that minor, same major.
PY_VERSION="$(sed -n 's/^python[[:space:]]*=[[:space:]]*"[^0-9]*\([0-9]\+\.[0-9]\+\).*/\1/p' pyproject.toml | head -1)"
PY_VERSION="${PY_VERSION:-3.14}"

# uv is the bootstrap tool (it provisions a standalone interpreter + Poetry). Pinned rather
# than "latest" so the bootstrap is reproducible and a version bump is a reviewable diff —
# the same discipline .pre-commit-config.yaml applies to its hook revs. Bump deliberately.
UV_BOOTSTRAP_VERSION="0.12.10"
# sha256 of https://astral.sh/uv/$UV_BOOTSTRAP_VERSION/install.sh, checked before the script is
# executed — a pinned URL alone still trusts whatever the CDN serves. Recompute when bumping:
#   curl -LsSf https://astral.sh/uv/<version>/install.sh | sha256sum
UV_BOOTSTRAP_SHA256="a3196b75f697a1adaa5e4af34ffba7629c710931ab1dac33bab59ecf228080bb"

PY=""       # interpreter satisfying the project's Python constraint
UV=""       # uv, used only as the provisioning tool (never a runtime dependency)
POETRY=""   # the poetry executable the rest of this script drives

die() { echo "  $*" >&2; exit 1; }

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
  else python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"
  fi
}

# Refuse to provision when the user opted out, explaining the manual path instead.
bootstrap_guard() {
  [ "${QENSEI_NO_BOOTSTRAP:-}" = "1" ] || return 0
  cat >&2 <<EOF
  $1 is missing, and QENSEI_NO_BOOTSTRAP=1 disables automatic provisioning.

  Install it yourself, then re-run \`make install\`:

    Python $PY_VERSION+   pyenv install $PY_VERSION  |  uv python install $PY_VERSION  |  your distro's package
    Poetry         pipx install poetry  |  curl -sSL https://install.python-poetry.org | python3 -

  Or drop QENSEI_NO_BOOTSTRAP to let \`make install\` provision both into ./.tooling.
EOF
  exit 1
}

# --- step 1: an interpreter matching pyproject's python constraint ----------
py_ok() {
  "$1" -c 'import sys; r = tuple(int(p) for p in sys.argv[1].split(".")); sys.exit(0 if sys.version_info[0] == r[0] and sys.version_info[:2] >= r else 1)' \
    "$PY_VERSION" 2>/dev/null
}

find_python() {
  local c
  for c in "python$PY_VERSION" python3 python; do
    if command -v "$c" >/dev/null 2>&1 && py_ok "$(command -v "$c")"; then
      PY="$(command -v "$c")"; return 0
    fi
  done
  # A previously provisioned standalone build (uv lays them out as <dir>/<build>/bin/python3).
  for c in "$TOOLING"/python/*/bin/python3; do
    if [ -x "$c" ] && py_ok "$c"; then PY="$c"; return 0; fi
  done
  return 1
}

ensure_python() {
  if find_python; then
    echo "==> python $PY_VERSION+ found: $PY ($("$PY" --version 2>&1))"
    return
  fi
  bootstrap_guard "Python $PY_VERSION"
  ensure_uv
  echo "==> provisioning a standalone Python $PY_VERSION into .tooling/python (no sudo)"
  # --no-bin keeps the interpreter fully inside .tooling: without it uv also drops a
  # ~/.local/bin/python$PY_VERSION symlink, which would dangle once .tooling is removed.
  # Older uv builds lack the flag, so probe for it (the env var covers those that honour it).
  local no_bin=""
  "$UV" python install --help 2>/dev/null | grep -q -- '--no-bin' && no_bin="--no-bin"
  UV_PYTHON_INSTALL_DIR="$TOOLING/python" UV_PYTHON_INSTALL_BIN=0 \
    "$UV" python install $no_bin "$PY_VERSION"
  find_python || die "provisioned Python $PY_VERSION but could not locate it under .tooling/python"
  echo "    $PY ($("$PY" --version 2>&1))"
}

# --- step 2: uv, the provisioning tool -------------------------------------
# uv is used ONLY to bootstrap (a standalone interpreter + Poetry). It is not a project
# dependency: the runtime stays stdlib-only and the dev toolchain stays Poetry-managed.
ensure_uv() {
  [ -n "$UV" ] && return 0
  if [ -x "$TOOLING_BIN/uv" ]; then
    UV="$TOOLING_BIN/uv"
  elif command -v uv >/dev/null 2>&1; then
    UV="$(command -v uv)"
  else
    command -v curl >/dev/null 2>&1 || die "curl is required to bootstrap the toolchain (install curl, or QENSEI_NO_BOOTSTRAP=1 and install Python $PY_VERSION + Poetry by hand)"
    echo "==> bootstrapping uv $UV_BOOTSTRAP_VERSION into .tooling/bin (no PATH or profile changes)"
    mkdir -p "$TOOLING_BIN"
    local installer="$TOOLING/uv-install.sh"
    curl -LsSf --proto '=https' --tlsv1.2 --max-time 120 \
      "https://astral.sh/uv/${UV_BOOTSTRAP_VERSION}/install.sh" -o "$installer" \
      || die "could not download the uv installer — check network access, or install Python $PY_VERSION + Poetry by hand"
    local got; got="$(sha256_of "$installer")"
    if [ "$got" != "$UV_BOOTSTRAP_SHA256" ]; then
      rm -f "$installer"
      die "uv installer checksum mismatch — refusing to execute it
    expected $UV_BOOTSTRAP_SHA256
    got      $got"
    fi
    # UV_UNMANAGED_INSTALL pins the install dir AND turns off both PATH edits and self-update.
    UV_UNMANAGED_INSTALL="$TOOLING_BIN" sh "$installer" >/dev/null
    rm -f "$installer"
    [ -x "$TOOLING_BIN/uv" ] || die "uv bootstrap did not produce $TOOLING_BIN/uv"
    UV="$TOOLING_BIN/uv"
  fi
  echo "==> uv: $UV ($("$UV" --version 2>&1))"
}

# --- step 3: Poetry ---------------------------------------------------------
ensure_poetry() {
  if [ -x "$TOOLING_BIN/poetry" ]; then
    POETRY="$TOOLING_BIN/poetry"          # the project-local one wins: it is what we provisioned
  elif command -v poetry >/dev/null 2>&1; then
    POETRY="$(command -v poetry)"
  else
    bootstrap_guard "Poetry"
    ensure_uv
    echo "==> installing Poetry into .tooling/bin (project-local, no sudo)"
    UV_TOOL_DIR="$TOOLING/uv-tools" UV_TOOL_BIN_DIR="$TOOLING_BIN" "$UV" tool install --python "$PY" poetry
    # uv warns that .tooling/bin is not on PATH — deliberately so: the make targets resolve
    # this Poetry by path (see the POETRY variable in the Makefile), no shell setup needed.
    echo "    (the PATH warning above is expected — the make targets use this Poetry directly)"
    [ -x "$TOOLING_BIN/poetry" ] || die "Poetry bootstrap did not produce $TOOLING_BIN/poetry"
    POETRY="$TOOLING_BIN/poetry"
  fi
  echo "==> poetry: $POETRY ($("$POETRY" --version 2>&1))"
}

ensure_python
ensure_poetry

echo "==> poetry install (pytest, pytest-xdist, ruff, pip-audit, playwright -> ./.venv)"
# Pin the venv to the interpreter resolved above: poetry would otherwise default to the
# `python3` on PATH, which may be older than the project's constraint.
"$POETRY" env use "$PY"
"$POETRY" install

echo "==> playwright install chromium (the browser the UI lane drives; ~150MB)"
"$POETRY" run playwright install chromium

cat <<EOF
==> dev toolchain ready. Common commands:
      make pytest    # REST + unit tests in parallel (pytest -n auto)
      make test-ui   # browser (Playwright) UI packs, headless
      make ui-watch  # watch the UI verification live (headed, slowed-down)
      make lint      # ruff lint
      make cve       # pip-audit dependency CVE scan
      make verify    # lint + cve + pytest + the offline gates
    The make targets find Poetry automatically. To call it directly, use:
      $POETRY run <tool>
EOF

if [ -d "$TOOLING" ]; then
  cat <<EOF
    The Python / Poetry / uv this script provisioned live in ./.tooling (gitignored);
    'rm -rf .tooling' reverts the bootstrap. (Playwright's browser binaries are the one
    thing outside the repo — they go to its own cache, ~/.cache/ms-playwright.)
EOF
fi

# --------------------------------------------------------------------------
# Claude Code integration (opt-in, project-scoped)
#
# Qensei is driven by an AI coding assistant. Its slash commands (commands/),
# review-panel subagents (agents/), and governance (policies/) only become
# discoverable once they live under ./.claude — Claude Code scans .claude/commands
# and .claude/agents at project scope. This step SYMLINKS them there, so the repo
# root stays the single source of truth (edits are live, no re-sync) and generates
# a ./.claude/CLAUDE.md that references the policies as governance.
#
# Project-scoped and opt-in: nothing is written to ~/.claude. ./.claude is
# gitignored, so the wiring is a local artifact — re-run `make install` to refresh.
# Set QENSEI_CLAUDE_WIRING=y to enable non-interactively (CI defaults to skip).
# --------------------------------------------------------------------------

# Generate ./.claude/CLAUDE.md (governance index). Paths are repo-root-relative:
# Claude Code runs with the repo root as cwd, so the assistant opens policies/… directly.
generate_claude_md() {
  cat <<'MD'
# Qensei — project instructions (generated by scripts/install.sh; do not hand-edit)

Qensei is an AI-assistant-driven QA framework. This file wires its governance into
Claude Code at project scope. It is regenerated by `make install`; the source of truth
is `policies/`, `commands/`, and `agents/` at the repo root.

## Governance — apply the policies in `policies/`
Product-neutral development governance. Read the relevant file when it applies:
- `policies/methodology.md` — spec-driven QA phases, spec conventions, ownership model
- `policies/testing-philosophy.md` — tests as behavioral contracts; real-downstream AC at integration boundaries
- `policies/communication-standards.md` — factual, neutral authoring for durable artifacts
- `policies/security-review.md` — mandatory dependency CVE scan + OWASP review
- `policies/input-hygiene.md` — credential/display/log hygiene
- `policies/release-safety.md` — reversibility / rollback discipline
- `policies/python-standards.md` — Python coding standards
- `policies/git-workflow.md` — commit/branch conventions (no AI-attribution trailers)

## Slash commands (`./.claude/commands` → `../commands`)
- `/automate` — turn a manually-tested ticket into an intent spec + regression pack
- `/validate` — verify a ticket over REST or UI
- `/report-bug` — file a structured bug for a genuine backend regression

## Review panel — subagents (`./.claude/agents` → `../agents`)
Advisory, read-only diagnostic lenses: `judge`, `r-diagnosis`, `r-evidence`,
`r-fidelity`, `r-coverage`, `r-mechanism`, `r-uplift`, and the design-stage `r-design` (runs at
`/automate` Phase 2b, before code exists). They raise the floor; they never gate a merge.
Whether a panel ran is recorded and linted (`engine/design_panel_lint.py` on `sut/<name>/plans/*.md`,
`engine/panel_section_lint.py` on validation reports) — the record is gated, the verdict never is.

## Domain knowledge — per SUT, loaded on demand (NOT loaded here)
Each product under test is a plugin under `sut/<name>/`. Its domain/system-shape
knowledge lives in `sut/<name>/skills/*.md` and accumulated `sut/<name>/learnings/*.md`,
declared in `sut/<name>/manifest.json` (`knowledge.skills` / `knowledge.learnings`).
These are intentionally NOT referenced globally: `/automate` and `/validate` load the
ACTIVE SUT's skills + learnings based on `--sut`, so only the relevant product's
knowledge enters context. Do not hardcode one SUT's skills in this file.

Discovered SUT skills:
MD
  local skill sut_name found=0
  for skill in sut/*/skills/*.md; do
    [ -f "$skill" ] || continue
    sut_name=$(basename "$(dirname "$(dirname "$skill")")")
    echo "- \`$sut_name\` — \`$skill\`"
    found=1
  done
  [ "$found" -eq 1 ] || echo "- (none discovered under sut/*/skills/)"
}

install_claude_wiring() {
  mkdir -p .claude
  ln -sfn ../commands .claude/commands
  ln -sfn ../agents   .claude/agents
  generate_claude_md > .claude/CLAUDE.md
  echo "  ./.claude/commands -> ../commands   (/automate, /validate, /report-bug)"
  echo "  ./.claude/agents   -> ../agents     (review panel: judge + r-* lenses)"
  echo "  ./.claude/CLAUDE.md                 (governance: policies/ + per-SUT skills pointer)"
  echo "  ./.claude is gitignored — re-run 'make install' to refresh the wiring."
  echo "  NOTE: (re)start Claude Code after first wiring so the review-panel lenses load"
  echo "        read-only — their tools: allowlist is applied at session start, not mid-session."
}

echo
if [ "${QENSEI_CLAUDE_WIRING:-}" = "y" ]; then
  reply="y"
elif [ -t 0 ]; then
  printf "==> Wire Qensei's commands, agents and policies into Claude Code (project-scoped ./.claude, symlinked)? [y/N] "
  read -r reply
else
  reply="n"   # non-interactive (CI): skip unless QENSEI_CLAUDE_WIRING=y
fi
case "$reply" in
  [Yy]*)
    echo "==> installing Claude Code integration (./.claude, symlinked to the repo root)"
    install_claude_wiring
    ;;
  *)
    echo "==> skipped Claude Code integration (re-run 'make install', or set QENSEI_CLAUDE_WIRING=y)"
    ;;
esac
