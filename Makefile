# Which SITE (SUT plugin) the targets act on. Override to test another site, e.g.
#   make test SUT=sut/restful-booker
# The diagnose/serve targets carry per-site defaults; `demo-booker` repoints them all.
SUT ?= sut/mock-shop
REALBUG_PACK ?= sut/mock-shop/packs/SHOP-456-discount
TESTBUG_PACK ?= sut/mock-shop/examples/diagnostics/SHOP-789-bad-test
SERVE_APP    ?= sut/mock-shop/source/app.py

.PHONY: help demo demo-booker design test smoke gate-report diagnose-realbug diagnose-testbug \
        serve check lint-offline test-engine fidelity coverage-lint design-panel panel-record citations freshness sync-source secrets new-sut new-pack new-ui-pack regen-index \
        install pytest test-ui ui-watch lint lint-fix cve verify

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-18s %s\n", $$1, $$2}'

# --- the three capabilities -------------------------------------------------
demo: design test diagnose-realbug diagnose-testbug ## full end-to-end walkthrough (mock-shop)

demo-booker: ## the same walkthrough against the restful-booker site
	$(MAKE) demo SUT=sut/restful-booker \
	  REALBUG_PACK=sut/restful-booker/packs/BOOK-2-longstay-discount \
	  TESTBUG_PACK=sut/restful-booker/examples/diagnostics/BOOK-789-bad-test \
	  SERVE_APP=sut/restful-booker/source/app.py

design: ## backend-aware coverage report (reads the SUT source)
	python3 -m engine.design --sut $(SUT)

test: ## regression gate against a healthy backend (green)
	python3 -m engine.run --sut $(SUT)

smoke: ## fast confidence slice (the smoke lane only)
	python3 -m engine.run --sut $(SUT) --select smoke

gate-report: ## gate + a machine-readable JUnit report (CI)
	python3 -m engine.run --sut $(SUT) --report report.xml

diagnose-realbug: ## seed a regression; the lens calls it REAL_BUG
	python3 -m engine.diagnose --sut $(SUT) --pack $(REALBUG_PACK) --seed-bug

diagnose-testbug: ## a deliberately wrong test; the lens calls it TEST_BUG
	python3 -m engine.diagnose --sut $(SUT) --pack $(TESTBUG_PACK)

serve: ## run the SUT's mock backend standalone (prints its port)
	python3 $(SERVE_APP)

# --- deterministic quality gates (the forcing functions) --------------------
check: test-engine fidelity coverage-lint design-panel panel-record lint-offline secrets ## offline pre-commit ritual (tests + fidelity + coverage-lint + panel records + lint + secrets)
	@echo "  check: OK"

lint-offline: ## ruff lint IF the toolchain is present (keeps `check` zero-dependency; CI always enforces it)
	@if command -v ruff >/dev/null 2>&1; then \
	  ruff check . && echo "  lint: clean"; \
	elif command -v $(POETRY) >/dev/null 2>&1 && $(POETRY) run ruff --version >/dev/null 2>&1; then \
	  $(POETRY) run ruff check . && echo "  lint: clean"; \
	else echo "  lint: skipped (ruff not installed — run 'make install'/'pre-commit install'; CI enforces it)"; fi

test-engine: ## unit tests for the engine core + gates
	python3 -m unittest discover -s tools/tests

fidelity: ## spec-fidelity lint — block a weakened acceptance criterion
	python3 -m engine.fidelity_lint

coverage-lint: ## coverage-metadata gate — case.py covers must match README + resolve against the SUT
	python3 -m engine.coverage_lint

design-panel: ## Phase-2b record — a plan changed vs HEAD must say whether R-DESIGN ran (+ per-finding dispositions)
	@python3 -m engine.design_panel_lint --changed

panel-record: ## Phase-4 record — a validation report changed vs HEAD must say whether the panel ran / was waived
	@python3 -m engine.panel_section_lint --changed

citations: ## resolve every source:line a lens cited (anti-fabrication)
	@git diff --name-only | xargs -r python3 -m engine.citation_gate || true

freshness: ## SUT source-clone freshness (no-op for in_process)
	python3 -m engine.freshness_gate --sut $(SUT)

sync-source: ## clone/refresh a remote SUT's source from source.repo (no-op for in-repo mocks)
	python3 -m engine.source_sync --sut $(SUT)

secrets: ## fail if an obvious secret is staged (best-effort, stdlib)
	@! git grep -nIE '(secret|password|token|api[_-]?key)\s*[:=]\s*["'\''][^"'\'' ]{12,}' -- ':!*.md' ':!Makefile' ':!.pre-commit-config.yaml' \
	  || (echo "  secrets: a hardcoded credential may be staged — review above" && exit 1)
	@echo "  secrets: clean"

# --- dev toolchain (Poetry: pytest + xdist, lint, CVE scan) -----------------
# `make check` above stays zero-dependency (stdlib unittest). The targets below need the
# Poetry-managed dev env — run `make install` once first. `make verify` is the full local CI.
#
# `make install` is self-bootstrapping: if Poetry (or the Python the project targets) is
# missing it provisions them into ./.tooling (gitignored, no sudo). That project-local
# Poetry wins over a system-wide one, so the targets below drive the toolchain install.sh
# actually set up. Override with `make pytest POETRY=/path/to/poetry`.
POETRY ?= $(shell if [ -x .tooling/bin/poetry ]; then echo .tooling/bin/poetry; else echo poetry; fi)

install: ## set up the dev/test toolchain (pytest+xdist, ruff, pip-audit) via Poetry
	./scripts/install.sh

pytest: ## run REST + unit tests under pytest + xdist (UI lane is opt-in: make test-ui)
	$(POETRY) run pytest -m "not ui"

test-ui: ## run the browser (Playwright) UI packs, headless and parallel (needs `make install`)
	$(POETRY) run pytest tests/test_ui.py

ui-watch: ## watch the UI verification LIVE — headed, slowed-down, single browser
	$(POETRY) run pytest tests/test_ui.py --headed --slowmo 600 -n0

lint: ## ruff lint over the codebase (needs `make install`)
	$(POETRY) run ruff check .

lint-fix: ## ruff lint applying safe autofixes
	$(POETRY) run ruff check --fix .

cve: ## scan dependencies for known CVEs with pip-audit (needs `make install`)
	$(POETRY) run pip-audit

verify: lint cve pytest fidelity coverage-lint secrets ## full local CI: lint + CVE + pytest + fidelity + coverage-lint + secrets
	@echo "  verify: OK"

# --- authoring tooling ------------------------------------------------------
new-sut: ## scaffold a NEW SUT plugin: make new-sut SUT=sut/acme [SOURCELESS=1]
	python3 scripts/new_sut.py $(SUT) $(if $(SOURCELESS),--sourceless,)

new-pack: ## scaffold a pack: make new-pack SUT=sut/mock-shop TICKET=SHOP-9 SLUG=widget-restock
	python3 scripts/new_pack.py --sut $(SUT) $(TICKET) $(SLUG)

new-ui-pack: ## scaffold a UI pack: make new-ui-pack SUT=sut/restful-booker TICKET=BOOK-UI-9 SLUG=cancel-flow
	python3 scripts/new_pack.py --sut $(SUT) --ui $(TICKET) $(SLUG)

regen-index: ## aggregate pack index cards into docs/delivered-regressions.md
	python3 scripts/regen_index.py
