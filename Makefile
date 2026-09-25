# Every quality gate is defined here once; CI runs these same targets, so a green
# `make check` locally means a green CI run. Run `make` to list the targets.

.DEFAULT_GOAL := help
.PHONY: help install fmt lint typecheck test check clean

help: ## List the available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-10s %s\n", $$1, $$2}'

install: ## Create the locked environment and install the git hooks
	uv sync --locked
	uv run pre-commit install

fmt: ## Format code and apply safe lint fixes
	uv run ruff format .
	uv run ruff check --fix .

lint: ## Check formatting and lint rules without changing files
	uv run ruff format --check .
	uv run ruff check .

typecheck: ## Type-check src/ and tests/ with mypy (strict)
	uv run mypy

test: ## Run tests and doctests with coverage
	uv run pytest --cov --cov-report=term-missing

check: lint typecheck test ## Run every gate that CI runs

clean: ## Remove caches, coverage data and build artefacts
	rm -rf .mypy_cache .pytest_cache .ruff_cache .coverage htmlcov build dist
