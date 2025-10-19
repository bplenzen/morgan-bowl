# Morgan Bowl Setup Guide

## Environment Setup ✅

**Status**: Complete

- Python 3.11.9 (via pyenv)
- Virtual environment in `.venv/`
- All dependencies installed via Poetry

## Quick Start: Get Your Data

### 1. Configure Your League

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add:

- **SLEEPER_LEAGUE_ID**: Find this in your Sleeper app URL when viewing your league
  - Example: `https://sleeper.com/leagues/1053946155782049792` → ID is `1053946155782049792`
- **SLEEPER_SEASON**: The year (e.g., `2024`)

### 2. Run Data Ingestion

```bash
# Ingest all weeks
poetry run python -m ingestion.cli

# Or ingest specific week(s)
poetry run python -m ingestion.cli --week 1 --week 2
```

This will:

1. Fetch data from Sleeper API (league info, rosters, matchups, users)
2. Store it in `data/warehouse.duckdb`
3. Track ingestion metadata

### 3. Verify Data

```bash
# Check what tables were created
poetry run python -c "import duckdb; con = duckdb.connect('data/warehouse.duckdb'); con.execute('SHOW TABLES').show()"

# View some data
poetry run python -c "import duckdb; con = duckdb.connect('data/warehouse.duckdb'); con.execute('SELECT * FROM raw_league LIMIT 5').show()"
```

## Project Structure (Cleaned Up)

```
morgan-bowl/
├── .venv/                   # Virtual environment (Python 3.11.9)
├── data/
│   └── warehouse.duckdb    # DuckDB database
├── src/ingestion/          # Data ingestion code
│   ├── cli.py             # Command-line interface
│   ├── client.py          # Sleeper API client
│   ├── config.py          # Configuration loading
│   ├── models.py          # Data models (Pydantic)
│   ├── persistence.py     # DuckDB storage
│   ├── pipeline.py        # Ingestion orchestration
│   └── versioning.py      # Version tracking
├── dbt/                    # DBT transformations (future)
└── tests/                  # Tests

Old/duplicate files archived in: archive/old-ingestion-20241014/
```

## Next Steps

For comprehensive next steps and future development plans, see:

📚 **[`docs/releases/NEXT_STEPS.md`](../releases/NEXT_STEPS.md)** - Complete guide to what to do next

Quick links:
- **Setup automation**: [`docs/setup/QUICK_START.md`](QUICK_START.md)
- **DBT development**: [`docs/guides/DBT_GUIDE.md`](../guides/DBT_GUIDE.md)
- **Feature roadmap**: [`docs/ROADMAP.md`](../ROADMAP.md)

## Troubleshooting

**Missing dependencies?**

```bash
poetry install
```

**Wrong Python version?**

```bash
poetry env use python3.11
poetry install
```

**Can't find your league ID?**

- Open Sleeper app
- Go to your league
- Look at the URL - the long number is your league ID
