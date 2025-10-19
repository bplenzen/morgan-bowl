# Morgan Bowl Fantasy Football Data Pipeline 🏈

A modern DataOps pipeline for analyzing Sleeper fantasy football data using Python, DBT, and DuckDB.

> 📚 **[View Full Documentation](docs/)** | 🗺️ **[Feature Roadmap](docs/ROADMAP.md)** | 🚀 **[Quick Start](docs/setup/QUICK_START.md)**

## 📊 Project Overview

This project demonstrates modern data engineering practices:

- **Data Ingestion**: Python scripts pull data from Sleeper API
- **Data Transformation**: DBT models create analytics-ready tables
- **Data Storage**: DuckDB embedded database (no server needed)
- **Orchestration**: GitLab CI/CD for scheduled weekly runs
- **Testing**: Pytest for Python code, DBT tests for data quality

## 🏗️ Architecture

```
Sleeper API → Python Ingestion → DuckDB → DBT Models → Analytics Tables
                                    ↓
                              GitLab CI/CD (Scheduled)
```

### Data Flow

1. **Ingestion** (`src/ingestion/`): Fetch data from Sleeper API weekly
2. **Staging** (`dbt/models/staging/`): Clean and standardize raw data
3. **Analytics** (`dbt/models/marts/`): Business logic and aggregations
4. **Consumption**: Query final tables for insights

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (via pyenv recommended)
- Poetry for dependency management
- Git for version control

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd morgan-bowl

# Install Python 3.11 (if using pyenv)
pyenv install 3.11.9
pyenv local 3.11.9

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your league ID

# Run initial data ingestion
poetry run python -m ingestion.cli --week 1

# Run DBT models
cd dbt
poetry run dbt run
poetry run dbt test
```

## 📁 Project Structure

```
morgan-bowl/
├── src/ingestion/          # Data ingestion from Sleeper API
│   ├── cli.py             # Command-line interface
│   ├── client.py          # API client
│   ├── config.py          # Configuration management
│   ├── persistence.py     # DuckDB storage layer
│   └── pipeline.py        # Orchestration logic
├── dbt/                   # DBT project
│   ├── models/
│   │   ├── staging/       # Raw data cleaning
│   │   └── marts/         # Analytics models
│   ├── tests/             # Custom DBT tests
│   └── dbt_project.yml    # DBT configuration
├── tests/                 # Pytest tests
├── scripts/               # Utility scripts
│   └── weekly_ingestion.py  # Auto-ingestion script
├── data/                  # DuckDB database
├── .gitlab-ci.yml         # CI/CD pipeline
└── pyproject.toml         # Python dependencies
```

## 🗄️ Database Schema

### Staging Layer

- `stg_league`: League information
- `stg_users`: Fantasy managers
- `stg_rosters`: Team rosters
- `stg_matchups`: Weekly matchup results

### Analytics Layer

- `fct_matchups`: Every game with opponent info, points, win/loss
- `fct_standings`: Current league standings with stats

## 🔄 Automated Ingestion

The pipeline runs automatically every Tuesday at 6:00 AM via GitLab CI/CD:

1. Detects current NFL week
2. Ingests missing weeks
3. Updates DBT models
4. Runs data quality tests
5. Stores results as artifacts

See [GITLAB_SETUP.md](GITLAB_SETUP.md) for configuration details.

## 🧪 Testing

```bash
# Run all Python tests
poetry run pytest tests/ -v

# Run DBT tests
cd dbt
poetry run dbt test

# Run specific test file
poetry run pytest tests/ingestion/test_persistence.py -v
```

## 📈 Example Queries

```python
import duckdb

conn = duckdb.connect('data/warehouse.duckdb')

# Current standings
standings = conn.execute("""
    SELECT manager_name, wins, losses, points_for, win_pct
    FROM main_analytics.fct_standings
    ORDER BY wins DESC, points_for DESC
""").fetchall()

# Your recent games
games = conn.execute("""
    SELECT week, opponent_manager_name, points, opponent_points,
           CASE WHEN win_flag = 1 THEN 'W' ELSE 'L' END as result
    FROM main_analytics.fct_matchups
    WHERE manager_name = 'YOUR_NAME'
    ORDER BY week DESC
    LIMIT 5
""").fetchall()
```

## 🛠️ Development

### Adding a New Week

```bash
# Manual ingestion for specific week
poetry run python -m ingestion.cli --week 7

# Auto-detect and ingest missing weeks
poetry run python scripts/weekly_ingestion.py
```

### Updating DBT Models

```bash
cd dbt
poetry run dbt run          # Run all models
poetry run dbt run -m marts # Run only marts models
poetry run dbt test         # Run tests
```

### Code Quality

```bash
# Linting
poetry run ruff check src/

# Type checking (if using mypy)
poetry run mypy src/

# Format code
poetry run ruff format src/
```

## 📚 Documentation

- [GitLab CI/CD Setup](GITLAB_SETUP.md) - Automated pipeline configuration
- [DBT Models](dbt/README.md) - Data transformation documentation
- [Architecture](docs/architecture.md) - System design and decisions

## 🎓 Learning Objectives

This project teaches:

- ✅ **API Integration**: RESTful API consumption with error handling
- ✅ **Data Modeling**: Dimensional modeling with DBT
- ✅ **SQL**: Advanced queries, CTEs, window functions
- ✅ **Testing**: Unit tests, integration tests, data quality tests
- ✅ **CI/CD**: GitLab pipelines, scheduled jobs, artifacts
- ✅ **Version Control**: Git workflow, branching, PRs
- ✅ **DataOps**: Automated data pipelines, monitoring, observability

## 🤝 Contributing

This is a learning project, but contributions welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

MIT License - feel free to use this for your own fantasy leagues!

## 🙏 Acknowledgments

- [Sleeper API](https://docs.sleeper.app/) - Fantasy football data
- [DBT](https://www.getdbt.com/) - Data transformation framework
- [DuckDB](https://duckdb.org/) - Embedded analytics database

---

**Current Season**: 2025
**League**: Morgan Bowl 4.0
**Last Updated**: October 2025 DataOps Lab

Morgan Bowl is a personal sandbox for end-to-end DataOps practice using Sleeper fantasy football data. The goal is to learn modern, low-cost tooling while exercising the full lifecycle from ingestion through observability.

## Learning Objectives

- Stand up a reproducible analytics engineering environment with dbt at the core.
- Practice batch ingestion, modeling, and automated quality checks against a public API.
- Build CI/CD and orchestration routines that mirror enterprise DataOps patterns.
- Deliver lightweight analytics artifacts (dashboards, docs) while monitoring data health.

## Architecture Overview

```
           +-----------------+        +----------------+
           | Sleeper API     |        | External Feeds |
           +--------+--------+        +--------+-------+
                    |                          |
                    v                          v
             +-------------+            +-------------+
             | Ingestion   |------------| Raw Landing |
             | Python/HTTP |            | DuckDB/Parquet
             +------+------+            +------+------+
                    |                          |
                    v                          v
              +------------+           +--------------+
              | dbt Staging|---------->| dbt Marts    |
              | (DuckDB)   |           | Facts/Dims   |
              +------+-----+           +------+-------+
                     |                         |
          +----------+-----------+             |
          | dbt Tests & Docs     |             |
          +----------+-----------+             |
                     |                         v
                     v                +----------------+
              +-------------+         | Lightdash /    |
              | Observability|<-------| Metabase       |
              | Elementary   |        +----------------+
                     ^
                     |
        +------------+-------------+
        | Orchestration (Prefect)  |
        | & GitLab CI/CD           |
        +--------------------------+
```

## Tool Stack

- **Source**: Sleeper fantasy football REST API.
- **Language & Package Management**: Python 3.11, Poetry, `ruff`, `black`, `isort`, `mypy`.
- **Storage & Compute**: DuckDB for local warehouse; Parquet for persisted raw extracts.
- **Transformation**: dbt Core with dbt-duckdb adapter; dbt-expectations for enhanced testing.
- **Orchestration**: Prefect (self-hosted) for deployment flows; GitLab CI/CD for lint/test/dbt automation.
- **Observability**: Elementary for dbt test monitoring; Prefect alerts; structured logging (`structlog` or stdlib logging).
- **Visualization**: Lightdash (dbt-native) or Metabase connected to DuckDB; Jupyter/Polars notebooks for ad hoc analysis.
- **Developer Experience**: VS Code devcontainer or `.vscode` workspace, pre-commit hooks, Makefile, direnv for environment variables.
- **Documentation**: Markdown in `docs/`, dbt docs site, architecture diagram source (Excalidraw/diagrams.net).

## Project Plan

1. **Setup**
   - Initialize Poetry project, pre-commit, `.editorconfig`, `.gitignore`.
   - Create repository skeleton (`src/`, `dbt/`, `analytics/`, `orchestration/`, `observability/`, `docs/`, `data/`).
   - Draft contribution guide, environment instructions, and architecture diagram source.
2. **Ingestion**
   - Explore Sleeper endpoints (league info, rosters, matchups, transactions, players).
   - Implement resilient API client with retries/backoff and schema validation.
   - Persist raw JSON snapshots and normalized Parquet tables in DuckDB staging schema.
   - Add unit tests with mocked responses and CLI entry point for batch pulls.
3. **Transformation**
   - Scaffold dbt project targeting DuckDB; define raw sources and staging models.
   - Build dimensional and fact models (players, teams, matchups, waivers).
   - Layer dbt tests, snapshots for slowly changing dimensions, and exposures.
   - Generate dbt docs and commit manifest/artifact guidance.
4. **Automation & CI/CD**
   - Author Makefile and Prefect flows covering ingestion + dbt run.
   - Configure GitLab CI pipeline (lint, pytest, dbt build, docs artifact).
   - Schedule nightly refresh pipeline and manual promotion jobs.
5. **Visualization**
   - Deploy Lightdash/Metabase via Docker Compose; connect to DuckDB.
   - Version dashboard definitions and align with dbt exposures.
   - Publish starter dashboards and data dictionary.
6. **Observability**
   - Integrate Elementary for dbt; surface reports via GitLab Pages or artifacts.
   - Capture ingestion logs, Prefect run metrics, and configure alerting (Slack/email).
   - Document SLAs, runbooks, and incident response workflow.

## Planned Repository Layout

```
morgan-bowl/
├── src/ingestion/           # Sleeper API clients, CLI, utilities
├── dbt/                     # dbt project (models, macros, tests)
├── analytics/               # Dashboards, notebooks, data dictionary
├── orchestration/           # Prefect deployments, schedules
├── observability/           # Elementary configs, alert hooks
├── infra/                   # Optional Terraform/compose definitions
├── docs/                    # Architecture diagrams, runbooks
├── data/raw/                # Raw JSON snapshots (gitignored)
├── data/processed/          # Parquet/DuckDB artifacts (gitignored)
├── tests/                   # Pytest suites for ingestion/utilities
└── Makefile
```

## Next Actions

- Commit initial scaffolding (Poetry, pre-commit, directory structure).
- Capture Sleeper league/season parameters and sample payloads.
- Open GitLab issues per plan milestone to track learning goals and deliverables.
