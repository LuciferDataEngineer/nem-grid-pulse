ROOT := $(CURDIR)
export PATH := $(HOME)/.local/bin:$(PATH)
export DUCKDB_PATH := $(ROOT)/data/warehouse/nem.duckdb
export BRONZE_ROOT := $(ROOT)/data/bronze
export DBT_PROFILES_DIR := $(ROOT)/dbt
export DBT_SEND_ANONYMOUS_USAGE_STATS := false

.PHONY: help ingest validate transform test lint dashboard insights all freshness

help:
	@echo "make ingest      Download new AEMO and Open Electricity partitions"
	@echo "make transform   Validate contracts and dbt build"
	@echo "make test        pytest and dbt test"
	@echo "make lint        ruff check and format check"
	@echo "make dashboard   Rebuild INSIGHTS.md and the static dashboard"
	@echo "make all         ingest, transform, test, lint, dashboard"

ingest:
	python -m nem_grid_pulse ingest

validate:
	python -m nem_grid_pulse validate

transform: validate
	mkdir -p $(ROOT)/data/warehouse
	dbt build --project-dir dbt --profiles-dir dbt

test:
	pytest
	dbt test --project-dir dbt --profiles-dir dbt

lint:
	ruff check src tests
	ruff format --check src tests

dashboard:
	python -m nem_grid_pulse insights
	python -m nem_grid_pulse dashboard

insights:
	python -m nem_grid_pulse insights

freshness:
	dbt source freshness --project-dir dbt --profiles-dir dbt

all: ingest transform test lint dashboard
