# Changelog

All notable changes to the Morgan Bowl Fantasy Football Analytics project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-10-19

### 🔒 Security

- **SQL Injection Prevention**: Replaced f-string SQL interpolation with parameterized queries in `scripts/generate_report.py`

### 🛡️ Fixed

- **Error Handling**: Added defensive try-except blocks to all dashboard data loading functions
- **Hardcoded Season**: Auto-detect season year from Sleeper API instead of hardcoding 2025
- **Hardcoded League Size**: Moved playoff team count (6) to DBT variables for flexibility

### 🧪 Testing

- Added `tests/test_sql_injection.py` - Educational tests for SQL injection prevention (4 tests)
- Added `tests/test_generate_report_secure.py` - Integration tests for secure report generation (3 tests)
- Added `tests/test_dashboard_errors.py` - Code structure validation for error handling (2 tests)
- Added `tests/ingestion/test_models.py` - Data model validation including season field (4 tests)

### 📚 Documentation

- Created `docs/releases/RELEASE_1.0.1.md` - Comprehensive release documentation
- Created `docs/learning_logs/01_sql_injection_prevention.md` - Educational resource on security

## [1.0.0] - 2025-10-14

### 🎉 Initial Release

#### Added - Data Pipeline

- **Sleeper API Integration**: Automated data ingestion from Sleeper fantasy football API
- **DuckDB Warehouse**: Embedded database for local analytics (no cloud costs!)
- **DBT Transformations**: Staging and analytics layers with proper dimensional modeling
- **Weekly Automation**: GitLab CI/CD pipeline with Tuesday 6 AM scheduled runs
- **Zero-Padded Weeks**: Consistent `week_01`, `week_02` naming convention

#### Added - Analytics Models

- **fct_matchups**: Week-by-week game results with opponent information and win/loss flags
- **fct_standings**: Current league standings with wins, losses, win%, points for/against
- **fct_justice_record**: 🌟 **KILLER FEATURE** - Luck analysis showing who's winning/losing more than they deserve
  - Top 6 scorers each week get "justice win"
  - Bottom 6 scorers get "justice loss"
  - Luck differential = actual wins - justice wins
  - Identifies lucky teams (🍀) and unlucky teams (😭)

#### Added - Testing & Quality

- **82 Total Tests**:
  - 23 Python unit tests (pytest)
  - 17 DBT data tests
  - 42 API parity integration tests (validates against Sleeper API as source of truth)
  - 1 custom justice balance test (verifies exactly 6 wins/6 losses per week)
- **SQL Injection Protection**: `_validate_identifier()` function prevents malicious table/column names
- **Comprehensive Error Handling**: Structured logging with context
- **Type Safety**: Pydantic models for API responses

#### Added - Visualization & Reporting

- **Streamlit Dashboard**: Interactive web app with 4 views:
  - 📊 Standings: Current league standings and points visualization
  - 🍀 Luck Analysis: Justice record with luck differential charts
  - 📈 Weekly Performance: Week-by-week scoring trends
  - 🔥 Power Rankings: Combined metric of wins, points, and luck
- **Weekly Report Generator**: Markdown reports with matchup results and luck analysis
- **Email/Slack Support**: Optional notification system (configure via environment variables)

#### Added - Documentation

- `README.md`: Project overview and architecture
- `QUICK_START.md`: 15-minute setup guide
- `GITLAB_SETUP.md`: CI/CD configuration walkthrough
- `docs/DATA_QUALITY.md`: Testing strategy and philosophy
- `docs/testing_strategy.md`: Test implementation roadmap
- `analytics/README.md`: Dashboard deployment guide
- `RELEASE_1.0.0.md`: Comprehensive release checklist

#### Security

- Environment variables protected (`.env` in `.gitignore`)
- GitLab CI/CD variables for secrets
- SQL injection prevention
- Read-only database connections in dashboard
- No sensitive data in code repository

### Technical Details

#### Stack

- **Python**: 3.11.9 (via pyenv)
- **Dependency Management**: Poetry 1.8.2
- **Database**: DuckDB 1.1.3 (embedded, no server needed)
- **Transformation**: DBT 1.10.13 with dbt-duckdb adapter
- **API Client**: httpx 0.27.2 with retry logic (tenacity)
- **Visualization**: Streamlit 1.50.0 + Plotly 6.3.1
- **Data Processing**: Polars 0.20.31 (fast DataFrame library)
- **CI/CD**: GitLab CI/CD with 3-stage pipeline (ingest → build → test)

#### Data Pipeline

1. **Ingestion** (`scripts/weekly_ingestion.py`):
   - Auto-detects current NFL week from Sleeper API
   - Identifies missing weeks in database
   - Ingests only new weeks (idempotent)
   - Runs DBT transformations after ingestion

2. **Staging Layer** (DBT):
   - `stg_league`: League configuration
   - `stg_users`: User/manager information
   - `stg_rosters`: Team rosters
   - `stg_matchups`: Weekly matchup results (unions weeks 1-6)

3. **Analytics Layer** (DBT):
   - `fct_matchups`: 72 rows (12 teams × 6 weeks)
   - `fct_standings`: 12 rows (1 per team)
   - `fct_justice_record`: 12 rows (1 per team) 🌟 NEW!

#### Project Structure

```
morgan-bowl/
├── src/ingestion/        # Python ingestion code
├── dbt/models/           # DBT transformations
│   ├── staging/          # Clean source data views
│   └── marts/            # Analytics tables
├── tests/                # Pytest unit & integration tests
├── dbt/tests/            # DBT data tests
├── scripts/              # Automation scripts
├── analytics/            # Streamlit dashboard
├── data/                 # DuckDB warehouse (7.8MB)
└── .gitlab-ci.yml        # CI/CD pipeline
```

### What's Next? (Roadmap to 1.1.0)

#### Potential Features

- Playoff probability simulator (Monte Carlo)
- Strength of schedule analysis
- Player-level performance tracking
- Trade analyzer
- Power rankings with momentum
- Email/Slack notifications (code ready, just needs configuration)

### Breaking Changes

- None (initial release)

### Deprecated

- None (initial release)

### Known Issues

- Sleeper projections API is deprecated/empty (confirmed via API exploration)
- Dashboard requires manual deployment to Streamlit Cloud for league-wide access

### Contributors

- Ben Lenzen (@bplenzen)

---

## [Unreleased]

### Planned for 1.1.0

- [ ] Playoff probability calculator
- [ ] Strength of schedule metrics
- [ ] Automated email/Slack notifications
- [ ] Player-level analytics

---

**Full Diff**: Initial release

**Note**: This project was built as a hands-on learning experience for modern DataOps practices, including ETL pipelines, DBT transformations, CI/CD automation, comprehensive testing, and interactive dashboards.
