# Job Market Tracker — common tasks. Run `make` to see targets.
# All DB settings come from environment / .env (see .env.example).

# Load .env (if present) so every target — Python and dbt alike — sees PG*.
ifneq (,$(wildcard .env))
include .env
export
endif

# Prefer the local 3.12 venv (holds app + browser + dbt); fall back to python3.
PY := $(shell [ -x .venv/bin/python ] && echo $(CURDIR)/.venv/bin/python || echo python3)
DBT_BIN := $(shell [ -x .venv/bin/dbt ] && echo $(CURDIR)/.venv/bin/dbt || command -v dbt 2>/dev/null || echo dbt)
export PYTHONPATH := $(CURDIR)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## --- Docker (recommended: zero local dependencies) -----------------------
.PHONY: up
up: ## Build + run everything in Docker (Postgres + pipeline + dbt)
	docker compose up --build

.PHONY: down
down: ## Stop containers and remove the database volume
	docker compose down -v

.PHONY: db-up
db-up: ## Start only the PostgreSQL container (for local pipeline runs)
	docker compose up -d db

.PHONY: db-down
db-down: ## Stop the PostgreSQL container (keeps the data volume)
	docker compose stop db

## --- Local (requires `uv`) -----------------------------------------------
.PHONY: setup
setup: ## Install local dependencies (app + dbt venv via uv)
	bash scripts/setup_local.sh

.PHONY: bootstrap
bootstrap: ## Ensure DB, load warehouse, run dbt (idempotent)
	bash scripts/bootstrap.sh

## --- Individual steps ----------------------------------------------------
.PHONY: scrape
scrape: ## Run producers (override which: `make scrape SOURCES="wuzzuf forasna"`)
	$(PY) -m producers.runner $(SOURCES)

.PHONY: sample
sample: ## Generate sample Silver data
	$(PY) warehouse/make_sample_data.py

.PHONY: pipeline
pipeline: ## Run the cleaning pipeline (Bronze -> Silver)
	$(PY) processing/main.py

.PHONY: load
load: ## Build warehouse schema + load Silver into Postgres
	$(PY) -m warehouse.load_to_postgres --init

.PHONY: dbt
dbt: ## Run dbt build (staging -> intermediate -> marts + tests)
	cd dbt/job_market_tracker && DBT_PROFILES_DIR=$(CURDIR)/dbt/job_market_tracker $(DBT_BIN) build

.PHONY: test
test: ## Run the warehouse + pipeline test suites
	$(PY) warehouse/test_phase4.py
	$(PY) warehouse/test_pipeline.py

.PHONY: stress
stress: ## Run the high-volume stress test (pipeline + warehouse + dbt)
	$(PY) warehouse/stress_test.py
