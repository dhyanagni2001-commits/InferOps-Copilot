PYTHON ?= .venv/bin/python
.DEFAULT_GOAL := help

help: ## List targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

install: ## Create .venv and install backend + frontend dependencies
	test -x $(PYTHON) || python3 -m venv .venv
	$(PYTHON) -m pip install -q -e './backend[dev,triton]'
	npm --prefix frontend ci

index: ## Build the local documentation index (hash embeddings)
	$(PYTHON) -m ingestion.build_index

dev: ## Run API on :8081 and UI on :5173 (demo mode)
	./scripts/dev.sh

lint: ## Lint Python
	$(PYTHON) -m ruff check backend ingestion evaluation scripts inference --config backend/pyproject.toml

test: ## Backend unit/API tests
	cd backend && ../$(PYTHON) -m pytest -q

test-ui: ## Build the UI and run Playwright browser tests
	npm --prefix frontend run build
	cd frontend && npx playwright test

eval: ## Evaluate scenario cases against a running API (BASE_URL, TOKEN)
	$(PYTHON) -m evaluation.run_evaluation --base-url $${BASE_URL:-http://127.0.0.1:8081} --token $${TOKEN:-dev-token}

eval-retrieval: ## Retrieval quality of the local hash index
	$(PYTHON) -m evaluation.retrieval_eval

e2e: ## Full kind cluster end-to-end run (needs docker, kind, kubectl)
	./scripts/kind-e2e.sh

fixtures: ## Re-record demo fixtures from scenarios running in the current cluster
	./scripts/run-scenario.sh all
	$(PYTHON) scripts/capture_fixtures.py

up: ## Docker Compose stack in demo mode on :8080
	docker compose up --build

.PHONY: help install index dev lint test test-ui eval eval-retrieval e2e fixtures up
