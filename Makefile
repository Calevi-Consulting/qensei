SUT ?= sut/mock-shop

.PHONY: help demo design test smoke gate-report diagnose-realbug diagnose-testbug serve \
        check test-engine fidelity citations freshness secrets new-pack regen-index

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-18s %s\n", $$1, $$2}'

# --- the three capabilities -------------------------------------------------
demo: design test diagnose-realbug diagnose-testbug ## full end-to-end walkthrough

design: ## backend-aware coverage report (reads the SUT source)
	python3 -m engine.design --sut $(SUT)

test: ## regression gate against a healthy backend (green)
	python3 -m engine.run --sut $(SUT)

smoke: ## fast confidence slice (the smoke lane only)
	python3 -m engine.run --sut $(SUT) --select smoke

gate-report: ## gate + a machine-readable JUnit report (CI)
	python3 -m engine.run --sut $(SUT) --report report.xml

diagnose-realbug: ## seed a regression; the lens calls it REAL_BUG
	python3 -m engine.diagnose --sut $(SUT) --pack packs/SHOP-456-discount --seed-bug

diagnose-testbug: ## a deliberately wrong test; the lens calls it TEST_BUG
	python3 -m engine.diagnose --sut $(SUT) --pack examples/diagnostics/SHOP-789-bad-test

serve: ## run the mock backend standalone (prints its port)
	python3 sut/mock-shop/source/app.py

# --- deterministic quality gates (the forcing functions) --------------------
check: test-engine fidelity secrets ## offline pre-commit ritual (tests + fidelity + secrets)
	@echo "  check: OK"

test-engine: ## unit tests for the engine core + gates
	python3 -m unittest discover -s tools/tests

fidelity: ## spec-fidelity lint — block a weakened acceptance criterion
	python3 -m engine.fidelity_lint

citations: ## resolve every source:line a lens cited (anti-fabrication)
	@git diff --name-only | xargs -r python3 -m engine.citation_gate || true

freshness: ## SUT source-clone freshness (no-op for in_process)
	python3 -m engine.freshness_gate --sut $(SUT)

secrets: ## fail if an obvious secret is staged (best-effort, stdlib)
	@! git grep -nIE '(secret|password|token|api[_-]?key)\s*[:=]\s*["'\''][^"'\'' ]{12,}' -- ':!*.md' ':!Makefile' ':!.pre-commit-config.yaml' \
	  || (echo "  secrets: a hardcoded credential may be staged — review above" && exit 1)
	@echo "  secrets: clean"

# --- authoring tooling ------------------------------------------------------
new-pack: ## scaffold a pack: make new-pack TICKET=SHOP-9 SLUG=widget-restock
	python3 scripts/new_pack.py $(TICKET) $(SLUG)

regen-index: ## aggregate pack index cards into docs/delivered-regressions.md
	python3 scripts/regen_index.py
