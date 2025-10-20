# Changelog

All notable changes to Morgan Bowl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2025-10-19

### Added

- **Draft Analysis**: Pick value curves, draft grades with frozen draft-day parameters
  - New model: `fct_draft_performance` (process-based grades)
  - New model: `fct_draft_realized_value` (in-season outcomes)
  - Draft parameter freeze system (`data/draft_day_parameters_2025.yml`)
  - No look-ahead bias - grades use only draft-day information
- **Luck Weight Calibration**: Statistical validation of composite luck score weights
  - Jupyter notebook: `analysis/luck_weight_calibration.ipynb`
  - Variance decomposition analysis (R² validation)
  - Sensitivity testing (±20% weight adjustments)
  - Data-driven weight recommendations
- **Advanced Luck Metrics**: Enhanced luck analysis with multiple components
  - New model: `fct_advanced_luck` (composite luck score)
  - Schedule luck index (opponent strength/timing)
  - Close game win percentage (coin-flip variance)
  - Wins over expected (aggregate luck metric)
- **FLEX Replacement Methodology**: Position-based value calculations
  - ADP-based FLEX slot allocation
  - Replacement level baselines by position
  - Academic justification documented

### Fixed

- Fixed look-ahead bias in draft grading (critical methodological fix)
- Fixed FLEX simulation to use projection-based approach (validated ADP as valid proxy)
- Fixed UTF-8 encoding issues in DBT SQL files
- Fixed ambiguous SQL references in `fct_advanced_luck`

### Changed

- Draft grades now use frozen draft-day parameters only
- Separated process-based grades from outcome-based value reports
- Updated `FLEX_REPLACEMENT_METHODOLOGY.md` with ADP scientific justification

### Documentation

- Added `docs/DRAFT_ANALYSIS_COMPLETE.md` - Full methodology
- Added `docs/DRAFT_ANALYSIS_METHODOLOGY.md` - Academic approach
- Added `docs/luck_weight_calibration_results.md` - Calibration findings
- Added `docs/WHITE_PAPER_luck_analysis.md` - Statistical foundations
- Added peer review documentation

---

## [1.1.0] - 2025-10-19

### Added

- **Universal League Configuration**: Auto-detect any Sleeper league settings
  - Expanded League model with 9 new fields (total_rosters, playoff_teams, etc.)
  - Configuration validator compares ingested vs DBT variables
  - Supports 8, 10, 12, 14+ team leagues
  - Auto-detects PPR/Half-PPR/Standard scoring
- **Enhanced League Model**: New fields in `stg_league`
  - `playoff_teams`, `playoff_week_start`, `total_rosters`, `settings`, `scoring_settings`
- **Configuration Validation**: `validate_league_configuration()` function
  - Reads `dbt_project.yml` and compares with league data
  - Logs helpful warnings if mismatches detected
  - Returns validation results

### Changed

- `fct_justice_record` now uses league metadata from `stg_league` table
- Models use COALESCE fallback to DBT vars for backwards compatibility
- No more hardcoded league-specific values

### Documentation

- Added "🌍 Use With ANY Sleeper League" section to README
- Step-by-step setup for different league formats

### Testing

- Added 13 new tests (all passing)
  - 5 League model tests
  - 8 configuration validator tests
- Total: 38 Python tests, 28 DBT tests

---

## [1.0.1] - 2025-10-19

### Security

- **SQL Injection Prevention**: Replaced f-string interpolation with parameterized queries
  - Fixed `scripts/generate_report.py` to use safe SQL execution

### Fixed

- **Error Handling**: Added defensive try-except blocks to dashboard data loading
- **Hardcoded Season**: Auto-detect season year from Sleeper API
- **Hardcoded League Size**: Moved playoff team count to DBT variables

### Testing

- Added `tests/test_sql_injection.py` - Educational SQL injection tests (4 tests)
- Added `tests/test_generate_report_secure.py` - Secure report generation tests (3 tests)
- Added `tests/test_dashboard_errors.py` - Error handling validation (2 tests)
- Added `tests/ingestion/test_models.py` - Data model validation (4 tests)

### Documentation

- Created `docs/releases/RELEASE_1.0.1.md`
- Created `docs/learning_logs/01_sql_injection_prevention.md`

---

## [1.0.0] - 2025-10-14

### Added - Data Pipeline

- **Sleeper API Integration**: Automated data ingestion from Sleeper API
- **DuckDB Warehouse**: Embedded database for local analytics
- **DBT Transformations**: Staging and analytics layers with dimensional modeling
- **Weekly Automation**: GitLab CI/CD pipeline with Tuesday 6 AM scheduled runs
- **Zero-Padded Weeks**: Consistent `week_01`, `week_02` naming convention

### Added - Analytics Models

- **fct_matchups**: Week-by-week game results with opponent info
- **fct_standings**: Current league standings (wins, losses, points for/against)
- **fct_justice_record**: Luck analysis (actual vs deserved record)
  - Top 50% scorers each week get "justice win"
  - Bottom 50% get "justice loss"
  - Luck differential = actual wins - justice wins

### Added - Testing & Quality

- **82 Total Tests**:
  - 23 Python unit tests (pytest)
  - 17 DBT data tests
  - 42 API parity integration tests
  - 1 custom justice balance test
- **SQL Injection Protection**: `_validate_identifier()` function
- **Comprehensive Error Handling**: Structured logging
- **Type Safety**: Pydantic models for API responses

### Added - Visualization & Reporting

- **Streamlit Dashboard**: Interactive web app with 4 views
  - 📊 Standings: Current league standings
  - 🍀 Luck Analysis: Justice record with luck charts
  - 📈 Weekly Performance: Week-by-week scoring trends
  - 🔥 Power Rankings: Combined metric (wins + points + luck)
- **Weekly Report Generator**: Markdown reports with matchup results
- **Email/Slack Support**: Optional notifications (via environment vars)

### Added - Documentation

- `README.md`: Project overview and architecture
- `docs/setup/QUICK_START.md`: 15-minute setup guide
- `docs/setup/GITLAB_SETUP.md`: CI/CD configuration
- `docs/DATA_QUALITY.md`: Testing strategy
- `analytics/README.md`: Dashboard deployment guide

### Technical Details

**Stack**:

- Python 3.11.9 (via pyenv)
- Poetry 1.8.2
- DuckDB 1.1.3
- DBT 1.10.13 with dbt-duckdb adapter
- httpx 0.27.2 with retry logic (tenacity)
- Streamlit 1.50.0 + Plotly 6.3.1
- Polars 0.20.31

**Data Pipeline**:

1. Ingestion: Auto-detect current week, ingest missing weeks
2. Staging: `stg_league`, `stg_users`, `stg_rosters`, `stg_matchups`
3. Analytics: `fct_matchups`, `fct_standings`, `fct_justice_record`

---

## [Unreleased]

### Planned for 2.0.0

- Multi-platform support (ESPN, Yahoo)
- Playoff probability simulator (Monte Carlo)
- Player-level performance tracking
- Trade analyzer
- Strength of schedule analysis
- Mobile app (React Native)

---

## Version History Summary

| Version | Date | Theme | Key Features |
|---------|------|-------|--------------|
| **1.2.0** | 2025-10-19 | Advanced Analytics | Draft analysis, luck calibration |
| **1.1.0** | 2025-10-19 | Universal Config | Any Sleeper league support |
| **1.0.1** | 2025-10-19 | Security & Fixes | SQL injection prevention |
| **1.0.0** | 2025-10-14 | Initial Release | Core pipeline, dashboard, justice record |

---

## Breaking Changes

None so far! All releases maintain backwards compatibility.

---

## Contributors

- Ben Lenzen (@bplenzen) - Project creator and maintainer

---

**Note**: This project is under active development. Expect frequent updates!
