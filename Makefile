.PHONY: bootstrap install lint format test dbt-build docs

bootstrap: ## Install dev tooling
	poetry install
	poetry run pre-commit install

install: ## Install project dependencies
	poetry install --sync

lint: ## Run static analysis
	poetry run ruff check .
	poetry run black --check .
	poetry run isort --check-only .
	poetry run mypy src

format: ## Auto-format code
	poetry run ruff check --fix .
	poetry run black .
	poetry run isort .

test: ## Run unit tests
	poetry run pytest

dbt-build: ## Run dbt build once dbt project is configured
	cd dbt && poetry run dbt build

docs: ## Regenerate dbt docs (placeholder)
	@echo "Docs generation not yet implemented"

help: ## Show available make targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
