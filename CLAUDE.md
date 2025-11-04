# CLAUDE.md

> **📌 LEAGUE BRANCH NOTE**
> This branch (`league-1251634383610187776`) is configured for **"The Uptown Letdowns"** fantasy football league.
>
> - League ID: `1251634383610187776`
> - Season: 2025
> - Team Count: 10 teams (not 12)
> - For the main Morgan Bowl 4.0 league, switch to the `main` branch.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Morgan Bowl is a modern analytics platform for Sleeper fantasy football leagues. It's a production-ready data pipeline that transforms raw fantasy football data into actionable insights using Python, DBT, and DuckDB.

**Key Technologies:**

- Python 3.11+ with Poetry dependency management
- DuckDB embedded database (`data/warehouse.duckdb`)
- DBT for SQL transformations
- Streamlit for interactive dashboard
- GitLab CI/CD for automated weekly data refresh

## Development Commands

### Initial Setup

```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env and add SLEEPER_LEAGUE_ID and SLEEPER_SEASON

# Pull initial data
poetry run python -m ingestion.cli

# Build analytics models
cd dbt && poetry run dbt build

# Launch dashboard
poetry run streamlit run analytics/dashboard.py
```

### Common Development Tasks

```bash
# Run all tests (Python + DBT)
make test                  # Python tests only
cd dbt && poetry run dbt test   # DBT data quality tests

# Linting and formatting
make lint                  # Check code style
make format                # Auto-format code

# Data ingestion
poetry run python -m ingestion.cli                 # All missing weeks
poetry run python -m ingestion.cli --week 6        # Specific week
poetry run python scripts/weekly_ingestion.py      # Auto-detect and ingest

# DBT operations
cd dbt
poetry run dbt build                    # Run all models + tests
poetry run dbt run                      # Run models only
poetry run dbt test                     # Run tests only
poetry run dbt run --select fct_standings   # Run single model
poetry run dbt deps                     # Install DBT packages
```

### Running Single Tests

```bash
# Python unit tests
poetry run pytest tests/ingestion/test_client.py -v
poetry run pytest tests/ingestion/test_pipeline.py::test_function_name -v

# DBT tests
cd dbt
poetry run dbt test --select fct_standings
poetry run dbt test --select marts.fct_advanced_luck
```

## Architecture

### Data Pipeline Flow

```
Sleeper API → Python Ingestion → DuckDB (raw_* tables) → DBT Staging → DBT Marts → Dashboard
```

### Three-Layer DBT Architecture

**1. Staging Layer** (`dbt/models/staging/`)

- Cleans and standardizes raw API data
- One table per API endpoint: `stg_league`, `stg_users`, `stg_rosters`, `stg_matchups`
- Also includes `stg_draft_picks`, `stg_player_stats`, `stg_preseason_rankings`
- Materialized as **views** for freshness

**2. Intermediate Layer** (`dbt/models/intermediate/`)

- Business logic calculations that feed into multiple marts
- Materialized as **ephemeral** (inline CTEs) to reduce table bloat
- Examples: `int_schedule_luck`, `int_wins_over_expected`, `int_close_game_outcomes`
- Draft analysis: `int_expected_value_by_pick`, `int_draft_day_baseline`, `int_opportunity_cost`

**3. Marts Layer** (`dbt/models/marts/`)

- Final analytics tables consumed by dashboard
- Materialized as **tables** for performance
- Core models: `fct_matchups`, `fct_standings`, `fct_advanced_luck`
- Advanced models: `fct_draft_performance`, `fct_draft_realized_value`, `fct_draft_grades`

### Python Package Structure

```
src/ingestion/
├── cli.py              # Command-line interface
├── client.py           # Sleeper API client with retry logic
├── models.py           # Pydantic data models (League, User, Roster, Matchup)
├── persistence.py      # DuckDB storage layer
├── pipeline.py         # Main orchestration with validation
├── config.py           # Configuration management
└── versioning.py       # API version tracking
```

### Key Design Patterns

**Idempotent Ingestion**: Safe to re-run; only pulls missing weeks. The pipeline checks existing data in `matchups_week_NN` tables and skips already-ingested weeks.

**Auto-Detection**: League configuration (size, playoff teams, season) is automatically detected from Sleeper API. The pipeline validates this against `dbt/dbt_project.yml` vars and logs warnings if mismatched.

**No Look-Ahead Bias**: Draft analysis uses frozen draft-day parameters. The `int_draft_day_baseline` model captures VOR/positional scarcity as they existed at draft time, not current values.

**Retry Logic**: All API calls use `tenacity` library with exponential backoff (3 attempts, 4-10 second waits).

## Important Behavioral Notes

### DBT Target Environments

The `dbt/profiles.yml` defines one target:

- **dev**: Points to `../data/warehouse.duckdb` (local development)

When running DBT commands, use:

- `dbt run` (defaults to dev)
- `dbt build --target ci` (used in GitLab CI/CD)

### Data Warehouse Location

**CRITICAL**: The DuckDB database is at `data/warehouse.duckdb` (relative to project root). All Python code, DBT models, and the dashboard read/write to this single file.

When writing code that accesses the database:

```python
# Correct path resolution
from pathlib import Path
db_path = Path(__file__).parent.parent / "data" / "warehouse.duckdb"

# Or from environment
import os
db_path = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
```

### DBT Model Dependencies

When creating new models, understand the layering:

- **Staging models** reference `raw_*` tables (created by Python ingestion)
- **Intermediate models** reference staging models (e.g., `{{ ref('stg_matchups') }}`)
- **Marts** reference intermediate and staging models

Use `{{ ref('model_name') }}` for dependencies, never hardcode table names.

### Testing Philosophy

**Python Tests** (38 tests):

- API client behavior and retry logic
- Data model validation (Pydantic)
- Pipeline orchestration
- SQL injection prevention
- Error handling

**DBT Tests** (28 tests):

- Data quality checks (not null, unique, accepted_values)
- Referential integrity (relationships)
- Custom business logic tests (e.g., `assert_no_lookahead_bias_draft.sql`)

Always add tests when adding new models or ingestion logic.

### CI/CD Pipeline (GitLab)

The `.gitlab-ci.yml` pipeline runs weekly (Tuesday 6 AM) and includes:

1. `ingest:weekly` - Pull data from Sleeper API
2. `dbt_build` - Compile and run all DBT models
3. `test:dbt` - Run DBT data quality tests
4. `test:python_unit` - Run Python unit tests
5. `test:api_parity` - Validate data against Sleeper API (SOURCE OF TRUTH)
6. `commit:data` - Commit updated `warehouse.duckdb` (manual trigger)
7. `mirror:github` - Sync to GitHub for Streamlit Cloud

**IMPORTANT**: The `test:api_parity` job is critical and will block the pipeline if data doesn't match the Sleeper API.

## Code Style and Conventions

- Use **Ruff** for linting (replaces flake8, isort)
- Use **Black** for formatting
- Use **mypy** for type checking
- All Python code should have type hints
- DBT models should include schema documentation in `schema.yml` files
- SQL should follow DBT style guide (lowercase keywords, 2-space indents)

## When Making Changes

**Adding a new DBT model:**

1. Determine correct layer (staging/intermediate/marts)
2. Create `.sql` file in appropriate directory
3. Add schema documentation in `schema.yml`
4. Add data quality tests (not_null, unique, relationships)
5. Run `dbt run --select your_model` to test
6. Run `dbt test --select your_model` to validate

**Adding new ingestion logic:**

1. Update Pydantic models in `src/ingestion/models.py` if needed
2. Add API client method in `src/ingestion/client.py`
3. Update pipeline logic in `src/ingestion/pipeline.py`
4. Write unit tests in `tests/ingestion/`
5. Test locally with `poetry run python -m ingestion.cli --week 1`

**Modifying the dashboard:**

1. Edit `analytics/dashboard.py`
2. Dashboard queries DuckDB directly (no DBT dependency)
3. Test locally: `poetry run streamlit run analytics/dashboard.py`
4. Dashboard reads from marts tables (e.g., `fct_standings`, `fct_advanced_luck`)

## Environment Variables

Required in `.env`:

- `SLEEPER_LEAGUE_ID` - Your Sleeper league ID (find in URL)
- `SLEEPER_SEASON` - Season year (e.g., 2025)
- `DUCKDB_PATH` - Database location (defaults to `data/warehouse.duckdb`)

GitLab CI/CD requires these as pipeline variables.

## Known Issues and Quirks

- **Draft analysis uses frozen draft-day baselines**: VOR and positional scarcity values are captured at draft time to avoid look-ahead bias. Don't use current player stats for draft grading.
- **Justice Record deprecated**: The `fct_justice_record` model has been replaced by `fct_advanced_luck` which includes schedule luck, close game outcomes, and wins over expected.
- **Week ingestion is idempotent**: Running ingestion for the same week twice will overwrite data (not append).
- **DBT vars auto-detected**: The `league_size` and `playoff_teams` variables in `dbt_project.yml` are compared against auto-detected values from the Sleeper API. Models use the auto-detected values, not the YAML vars.

## Research Notebooks

The `analysis/` directory contains Jupyter notebooks for statistical validation:

- `luck_weight_calibration.ipynb` - Validates composite luck score formula
- `draft_pick_value_curve.ipynb` - Models draft pick expected value
- `draft_uncertainty_analysis.ipynb` - Quantifies draft outcome variance
- `draft_flex_simulation_comparison.ipynb` - Compares draft strategies

These read from the same `data/warehouse.duckdb` as the dashboard.
