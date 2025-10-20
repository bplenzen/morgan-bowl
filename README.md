# Morgan Bowl 🏈

**Modern analytics platform for Sleeper fantasy football leagues**

A production-ready data pipeline that transforms raw fantasy football data into actionable insights using Python, DBT, and DuckDB.

---

## What Is This?

Morgan Bowl automatically pulls data from your Sleeper fantasy football league and creates:

- **📊 Interactive Dashboard**: Real-time standings, luck analysis, and power rankings
- **🎯 Advanced Analytics**: Draft grades, injury impact, strength of schedule
- **🤖 Automated Updates**: Weekly data refresh via GitLab CI/CD
- **📈 Data Warehouse**: All your league history in a local DuckDB database

**Best part?** Works with **any Sleeper league** - just provide your league ID.

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management

### Setup (5 minutes)

```bash
# 1. Clone and install
git clone <your-repo-url>
cd morgan-bowl
poetry install

# 2. Configure your league
cp .env.example .env
# Edit .env and add your SLEEPER_LEAGUE_ID

# 3. Pull data
poetry run python -m ingestion.cli

# 4. Build analytics
cd dbt
poetry run dbt build

# 5. Launch dashboard
poetry run streamlit run analytics/dashboard.py
```

Visit `http://localhost:8501` to see your dashboard!

---

## How to Find Your League ID

1. Open [Sleeper](https://sleeper.com) and go to your league
2. Look at the URL: `https://sleeper.com/leagues/YOUR_LEAGUE_ID`
3. Copy the long number (e.g., `1260408876017143808`)
4. Add to `.env`: `SLEEPER_LEAGUE_ID=1260408876017143808`

The system automatically detects:

- League size (8, 10, 12, 14+ teams)
- Playoff structure
- Scoring format (PPR, Half-PPR, Standard)
- Season year

---

## Project Structure

```
morgan-bowl/
├── src/ingestion/           # Python data ingestion from Sleeper API
│   ├── cli.py              # Command-line interface
│   ├── client.py           # API client with retry logic
│   ├── models.py           # Pydantic data models
│   ├── persistence.py      # DuckDB storage layer
│   └── pipeline.py         # Orchestration logic
│
├── dbt/                     # DBT transformations
│   ├── models/
│   │   ├── staging/        # Clean raw data
│   │   └── marts/          # Analytics tables
│   └── dbt_project.yml     # DBT configuration
│
├── analytics/               # Streamlit dashboard
│   └── dashboard.py        # Interactive web app
│
├── data/
│   └── warehouse.duckdb    # Embedded DuckDB database
│
├── scripts/
│   ├── weekly_ingestion.py # Automation script
│   └── generate_report.py  # Markdown reports
│
└── tests/                   # Pytest tests
```

---

## Usage

### Manual Data Refresh

```bash
# Ingest all missing weeks
poetry run python -m ingestion.cli

# Ingest specific week
poetry run python -m ingestion.cli --week 6

# Rebuild analytics
cd dbt && poetry run dbt build
```

### Run Dashboard

```bash
poetry run streamlit run analytics/dashboard.py
```

### Generate Weekly Report

```bash
poetry run python scripts/generate_report.py --week 6
```

---

## Features

### 📊 Core Analytics

| Feature | Description | Status |
|---------|-------------|--------|
| **Standings** | Win/loss records, points for/against | ✅ v1.0 |
| **Justice Record** | Luck analysis (who deserves their record?) | ✅ v1.0 |
| **Power Rankings** | Combined wins + points + luck metric | ✅ v1.0 |
| **Draft Analysis** | Pick value curves, draft grades | ✅ v1.2 |
| **Injury Impact** | Games lost to injuries, VORP analysis | ✅ v1.2 |
| **Luck Calibration** | Statistical validation of luck weights | ✅ v1.2 |

### 🤖 Automation

- **GitLab CI/CD**: Automated weekly data refresh (Tuesday 6 AM)
- **Idempotent Ingestion**: Safe to re-run, only pulls missing weeks
- **Error Handling**: Comprehensive logging and retry logic
- **Data Quality Tests**: 28 DBT tests + 38 Python tests

### 📈 Advanced Analytics

**Justice Record** (Luck Analysis):

- Each week, top 50% of scorers get "justice win", bottom 50% get "justice loss"
- Compare actual record vs deserved record
- Identify lucky/unlucky teams

**Draft Analysis**:

- Pick value curves (when to draft each position)
- Draft grades based on projected vs actual value
- Frozen draft-day parameters (no look-ahead bias)

**Injury Impact**:

- Games lost to injuries
- VORP (Value Over Replacement Player)
- Injury luck vs team quality

---

## Tech Stack

| Component | Technology | Why? |
|-----------|------------|------|
| **Language** | Python 3.11 | Modern, type-safe |
| **API Client** | httpx + tenacity | Async + retry logic |
| **Database** | DuckDB | Fast, embedded, no server |
| **Transformations** | DBT | SQL-based, testable |
| **Dashboard** | Streamlit | Fast prototyping |
| **Visualization** | Plotly | Interactive charts |
| **Data Processing** | Polars | 10x faster than Pandas |
| **CI/CD** | GitLab | Scheduled pipelines |
| **Testing** | Pytest + DBT tests | 66 total tests |

---

## Data Pipeline

```
Sleeper API → Python Ingestion → DuckDB → DBT Models → Analytics
                                    ↓
                              GitLab CI/CD
                             (Weekly Tuesday)
```

### Pipeline Stages

1. **Ingestion** (`src/ingestion/`):
   - Fetch league, rosters, matchups, users from Sleeper API
   - Store in `raw_*` tables in DuckDB
   - Track metadata (week, timestamp, API version)

2. **Staging** (`dbt/models/staging/`):
   - Clean field names, standardize types
   - Union multi-week data
   - `stg_league`, `stg_users`, `stg_rosters`, `stg_matchups`

3. **Analytics** (`dbt/models/marts/`):
   - Business logic and aggregations
   - `fct_matchups`, `fct_standings`, `fct_justice_record`
   - `fct_draft_performance`, `fct_injury_impact`, `fct_advanced_luck`

4. **Consumption**:
   - Streamlit dashboard reads from marts
   - Weekly Markdown reports
   - Optional Slack/email notifications

---

## Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for advanced setup:

- DBT profiles
- Streamlit secrets
- Environment variables
- GitLab CI/CD variables

---

## Testing

```bash
# Python tests
poetry run pytest

# DBT tests
cd dbt && poetry run dbt test

# All tests
make test
```

### Running Analysis Notebooks

Research notebooks in `analysis/` demonstrate advanced statistical methodology and validate model assumptions:

```bash
# Install Jupyter (if not already installed)
pip install jupyter ipykernel

# Launch Jupyter
jupyter notebook analysis/

# Or use VS Code's built-in notebook support
```

**Key Notebooks:**

- **`luck_weight_calibration.ipynb`** - Empirically validates composite luck score formula weights using variance decomposition, linear regression, and sensitivity testing. Responds to peer review feedback with data-driven recommendations (R² analysis, Spearman correlation).
- **`draft_pick_value_curve.ipynb`** - Models draft pick expected value using historical performance data
- **`draft_uncertainty_analysis.ipynb`** - Quantifies variance in draft outcomes across 10,000+ simulations
- **`draft_flex_simulation_comparison.ipynb`** - Compares draft strategies and FLEX position replacement value

These notebooks use the same DuckDB warehouse (`data/warehouse.duckdb`) as the dashboard and DBT models.

**Test Coverage**:

- 38 Python tests (API, ingestion, models, pipeline)
- 28 DBT tests (data quality, referential integrity)
- SQL injection prevention tests
- Error handling validation

---

## Deployment

### Local Development

Already covered in [Quick Start](#quick-start).

### Automated Weekly Updates (GitLab CI/CD)

1. Push code to GitLab
2. Configure CI/CD variables (Settings → CI/CD → Variables):
   - `SLEEPER_LEAGUE_ID`
   - `SLEEPER_SEASON`
3. Create pipeline schedule (Build → Pipeline Schedules):
   - Cron: `0 6 * * 2` (Tuesday 6 AM)
   - Branch: `main`

See [CONFIGURATION.md](CONFIGURATION.md) for detailed setup.

### Dashboard Deployment (Streamlit Cloud)

1. Push code to GitHub/GitLab
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo, set path: `analytics/dashboard.py`
4. Deploy (free!)

---

## FAQ

**Q: Does this work with ESPN/Yahoo leagues?**
A: Not yet. v2.0 will add ESPN/Yahoo support.

**Q: Can I use this for dynasty/best ball leagues?**
A: Partially. Core features work, but some analytics assume redraft format. Full support in v2.0.

**Q: What if I have a 14-team league?**
A: Works perfectly! Auto-detects league size from Sleeper API.

**Q: How much does this cost to run?**
A: $0. Everything runs locally or on free tiers (Streamlit Cloud, GitLab CI/CD).

**Q: Do I need to know SQL/Python?**
A: No! Just follow the Quick Start. To customize, basic SQL helps.

---

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new features
4. Run tests (`make test`)
5. Submit pull request

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features.

**Coming in v2.0**:

- Multi-platform support (ESPN, Yahoo)
- Playoff probability simulator
- Trade analyzer
- Player-level analytics
- Mobile app (React Native)

---

## License

MIT License - use however you want!

---

## Credits

Built by [Ben Lenzen](https://github.com/bplenzen) as a hands-on learning project for modern DataOps practices.

**Technologies learned**:

- ETL pipeline design
- DBT transformations
- DuckDB embedded analytics
- GitLab CI/CD automation
- Streamlit dashboards
- Fantasy football is data-driven fun

---

## Support

- **Issues**: [GitHub Issues](https://github.com/bplenzen/morgan-bowl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bplenzen/morgan-bowl/discussions)
- **Email**: <ben@example.com>

---

**⭐ If this helps your league, star the repo!**
