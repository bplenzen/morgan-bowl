# Release 1.1.0 - Universal League Configuration

**Release Date**: October 19, 2025  
**Theme**: Making Morgan Bowl Work for Any Sleeper League

## 🎯 Overview

Version 1.1.0 transforms Morgan Bowl from a project tailored to one specific league into a **universal analytics platform** that works with any Sleeper fantasy football league. Simply provide your league ID and the system automatically detects all configuration settings.

## ✨ Major Features

### 🌍 Universal League Configuration

Morgan Bowl now automatically detects and adapts to ANY Sleeper league:

- **Auto-Detection**: Fetches extended league settings from Sleeper API
  - Total teams (8, 10, 12, 14+ supported)
  - Playoff teams (4, 6, 8 teams)
  - Playoff week start
  - Season year
  - Scoring system (PPR, Half-PPR, Standard)
  - Roster positions

- **Configuration Validator**: Compares auto-detected settings with DBT variables
  - Logs helpful warnings if mismatches detected
  - Includes validation results in ingestion summary
  - Gracefully handles missing or incomplete configuration

- **DBT Model Updates**: Models now use league metadata from database
  - `fct_justice_record` uses `stg_league` table for playoff_teams
  - COALESCE fallback to DBT vars for backwards compatibility
  - No hardcoded league-specific values

- **Comprehensive Documentation**: New "🌍 Use With ANY Sleeper League" section
  - Step-by-step setup instructions
  - How to find your Sleeper league ID
  - What settings are auto-detected
  - Examples for different league sizes

## 📊 Technical Changes

### New Features

- **Expanded League Model** (`src/ingestion/models.py`)
  - Added 9 new fields: `total_rosters`, `playoff_teams`, `playoff_week_start`, `status`, `settings`, `scoring_settings`, `roster_positions`
  - Custom `model_validate()` extracts nested settings to top-level fields
  - Handles missing/incomplete data gracefully

- **Configuration Validator** (`src/ingestion/pipeline.py`)
  - New `validate_league_configuration()` function
  - Reads `dbt_project.yml` and compares with ingested league data
  - Returns validation results dict: `league_size_match`, `playoff_teams_match`, `validation_passed`
  - Logs structured warnings with recommendations

- **Enhanced Staging Model** (`dbt/models/staging/stg_league.sql`)
  - Exposes 5 new configuration fields
  - Documented in `staging_models.yml` with data tests
  - Used by downstream marts for dynamic configuration

### Updated Models

- **`fct_justice_record`**: Now uses league metadata from `stg_league` table
  - Adds `league_config` CTE with cross join
  - Uses `lc.playoff_teams` instead of hardcoded `var('playoff_teams')`
  - COALESCE ensures backwards compatibility

### Testing

Added 13 comprehensive tests (all passing):

**League Model Tests** (`tests/ingestion/test_models.py`):
- `test_league_extracts_nested_settings` - Verifies settings extraction
- `test_league_handles_missing_settings_fields` - Handles incomplete data
- `test_league_different_sizes` - Works with 8, 10, 12, 14 team leagues

**Validator Tests** (`tests/ingestion/test_pipeline.py`):
- `test_validate_league_configuration_matching` - Passes on match
- `test_validate_league_configuration_mismatched_size` - Detects size mismatch
- `test_validate_league_configuration_mismatched_playoffs` - Detects playoff mismatch
- `test_validate_league_configuration_both_mismatched` - Detects multiple mismatches
- `test_validate_league_configuration_missing_file` - Handles missing config
- `test_validate_league_configuration_missing_league_values` - Handles missing league data
- `test_validate_league_configuration_missing_dbt_vars` - Handles missing DBT vars
- `test_validate_league_configuration_different_league_sizes` - Multiple league formats

**Test Results**:
- ✅ 38 Python tests passing (pytest)
- ✅ 28 DBT tests passing (dbt test)

## 📦 Files Changed

### Core Logic
- `src/ingestion/models.py` - Expanded League model
- `src/ingestion/pipeline.py` - Added validator

### DBT Models
- `dbt/models/staging/stg_league.sql` - New fields
- `dbt/models/staging/staging_models.yml` - Documentation
- `dbt/models/marts/fct_justice_record.sql` - Uses league metadata

### Tests
- `tests/ingestion/test_models.py` - 5 new League tests
- `tests/ingestion/test_pipeline.py` - 8 new validator tests (NEW FILE)

### Documentation
- `README.md` - New "Use With ANY Sleeper League" section
- `docs/ROADMAP.md` - Marked v1.1.0 complete

## 🚀 Usage

### For New Users

```bash
# 1. Find your Sleeper league ID
# Go to: https://sleeper.com/leagues/YOUR_LEAGUE_ID

# 2. Configure environment
echo "SLEEPER_LEAGUE_ID=YOUR_LEAGUE_ID" > .env
echo "SLEEPER_SEASON=2025" >> .env

# 3. Run ingestion - settings auto-detected!
poetry run python -m ingestion.cli

# 4. Build analytics
cd dbt && poetry run dbt build
```

### Supported League Formats

- ✅ Standard leagues (12 teams, 6 playoff spots)
- ✅ Small leagues (8-10 teams)
- ✅ Large leagues (14+ teams)
- ✅ Custom playoff structures (4, 6, 8 playoff teams)
- ✅ PPR, Half-PPR, Standard scoring
- ⏳ Dynasty leagues (coming in v2.0)
- ⏳ Best Ball leagues (coming in v2.0)

## 🔍 What Gets Auto-Detected

Morgan Bowl now automatically pulls from Sleeper API:

- **League Size**: Total number of teams
- **Playoff Structure**: How many teams make playoffs
- **Playoff Start**: Which week playoffs begin
- **Season Year**: Current season
- **Scoring System**: PPR/Half-PPR/Standard settings
- **Roster Positions**: Starting lineup format

No manual configuration needed!

## 🐛 Bug Fixes

- Fixed UTF-8 encoding issues in DBT SQL files (corrupted emojis)
- Fixed ambiguous SQL references in `fct_advanced_luck`
- Updated `accepted_values` tests to remove emoji characters

## 📝 Breaking Changes

**None!** This release is fully backwards compatible:

- Existing `dbt_project.yml` vars still work
- Models use COALESCE to fall back to vars if league data unavailable
- No changes to data warehouse schema

## 🎓 Lessons Learned

- **Pydantic `model_validate()`** is great for extracting nested API data
- **YAML parsing** in Python is straightforward with PyYAML
- **DBT CTEs with cross joins** enable dynamic configuration
- **Validation logging** helps users understand mismatches
- **Comprehensive tests** catch edge cases early

## 📈 Impact

**High Impact**:
- Makes Morgan Bowl usable by anyone with a Sleeper league
- No more hardcoded league-specific values
- Sets foundation for ESPN/Yahoo support (v2.0)

## 🔗 Related Issues

- Closes #3: Hardcoded league configuration
- Implements: Universal league support from ROADMAP

## 👏 Contributors

- @bplenzen - Implementation, testing, documentation

---

**Next Up**: v1.2.0 - Advanced Analytics (Injury Impact, Draft Analysis, Strength of Schedule)
