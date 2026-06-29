SUT ?= sut/mock-shop

.PHONY: demo design test diagnose-realbug diagnose-testbug serve help

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-18s %s\n", $$1, $$2}'

demo: design test diagnose-realbug diagnose-testbug ## full end-to-end walkthrough

design: ## backend-aware coverage report (reads the SUT source)
	python3 -m engine.design --sut $(SUT)

test: ## regression gate against a healthy backend (green)
	python3 -m engine.run --sut $(SUT)

diagnose-realbug: ## seed a regression; the lens calls it REAL_BUG
	python3 -m engine.diagnose --sut $(SUT) --pack packs/SHOP-456-discount --seed-bug

diagnose-testbug: ## a deliberately wrong test; the lens calls it TEST_BUG
	python3 -m engine.diagnose --sut $(SUT) --pack examples/diagnostics/SHOP-789-bad-test

serve: ## run the mock backend standalone (prints its port)
	python3 sut/mock-shop/source/app.py
