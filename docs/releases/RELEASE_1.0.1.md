# Release 1.0.1 - Critical Fixes

**Release Date:** October 19, 2025
**Type:** Patch Release
**Status:** In Development

## Overview

This patch release addresses critical security vulnerabilities, adds defensive error handling, and removes hardcoded configuration values from the codebase. The release maintains backward compatibility while improving robustness and flexibility.

## Fixes Implemented

### 🔒 Security (CRITICAL)

**#2: SQL Injection Prevention**

- **File:** `scripts/generate_report.py`
- **Change:** Replaced f-string SQL interpolation with parameterized queries
- **Before:** `f"WHERE week = {week}"`
- **After:** `"WHERE week = ?"` with `[week]` parameter
- **Impact:** Prevents SQL injection attacks in report generation
- **Tests:** `tests/test_sql_injection.py` (4 tests), `tests/test_generate_report_secure.py` (3 tests)

### 🛡️ Error Handling

**#3: Dashboard Error Handling**

- **File:** `analytics/dashboard.py`
- **Change:** Added try-except blocks to all data loading functions
- **Pattern:** Catch exceptions → display user-friendly error → return empty DataFrame
- **Functions Updated:** `load_standings()`, `load_matchups()`, `load_justice_record()`, `load_advanced_luck()`
- **Impact:** Dashboard no longer crashes on database errors
- **Tests:** `tests/test_dashboard_errors.py` (2 code structure tests)

### ⚙️ Configuration Flexibility

**#4: Parameterize League Size**

- **Files:** `dbt/dbt_project.yml`, `dbt/models/marts/fct_justice_record.sql`
- **Change:** Moved hardcoded values to DBT variables
- **Variables Added:**
  - `league_size: 12` (total teams)
  - `playoff_teams: 6` (teams making playoffs)
- **Usage:** `{{ var('playoff_teams', 6) }}` in SQL models
- **Impact:** Easily adaptable to different league configurations
- **Validation:** DBT compilation successful

**#5: Auto-Detect Season Year**

- **Files:** `src/ingestion/models.py`, `src/ingestion/pipeline.py`
- **Change:** Extract season from Sleeper API instead of hardcoding
- **Model Update:** Added `season: Optional[str]` field to `League` model
- **Pipeline Logic:** Fetch league → extract `int(league.season)` → use for validation
- **Impact:** No code changes needed when rolling over to new season
- **Tests:** `tests/ingestion/test_models.py` (2 season-specific tests)

## Testing Summary

### Test Files Created

1. `tests/test_sql_injection.py` - Educational tests for SQL injection prevention
2. `tests/test_generate_report_secure.py` - Integration tests for secure report generation
3. `tests/test_dashboard_errors.py` - Code structure validation for error handling patterns
4. `tests/ingestion/test_models.py` - Data model validation including season field

### Test Results

- **Total Tests:** 13
- **Passing:** 13 ✅
- **Failed:** 0
- **Coverage:** Security, error handling, configuration, data models

```
tests/test_sql_injection.py ................. 4 passed
tests/test_generate_report_secure.py ........ 3 passed
tests/test_dashboard_errors.py .............. 2 passed
tests/ingestion/test_models.py .............. 4 passed
```

## Files Changed

| File | Type | Lines Changed | Description |
|------|------|---------------|-------------|
| `scripts/generate_report.py` | Modified | ~10 | Parameterized SQL queries |
| `analytics/dashboard.py` | Modified | ~40 | Added try-except blocks |
| `dbt/dbt_project.yml` | Modified | +3 | Added vars section |
| `dbt/models/marts/fct_justice_record.sql` | Modified | 1 | Use DBT variable |
| `src/ingestion/models.py` | Modified | +1 | Added season field |
| `src/ingestion/pipeline.py` | Modified | ~5 | Auto-detect season |
| `tests/test_sql_injection.py` | Created | 62 | New test file |
| `tests/test_generate_report_secure.py` | Created | 72 | New test file |
| `tests/test_dashboard_errors.py` | Created | 30 | New test file |
| `tests/ingestion/test_models.py` | Created | 62 | New test file |

## Upgrade Instructions

### No Breaking Changes

This release maintains full backward compatibility. No configuration changes are required.

### Optional Configuration

If using a different league configuration, update `dbt/dbt_project.yml`:

```yaml
vars:
  league_size: 12      # Change to your league size
  playoff_teams: 6     # Change to your playoff teams
```

### Validation Steps

1. Run tests: `poetry run pytest tests/ -v`
2. Compile DBT models: `cd dbt && poetry run dbt compile`
3. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
4. Generate report: `poetry run python scripts/generate_report.py <week>`

## Known Issues

None identified in this release.

## Migration Notes

### From 1.0.0 → 1.0.1

- No database migrations required
- No API changes
- No configuration changes required
- All existing data remains compatible

## Next Steps

For comprehensive next steps and future development plans, see:

📚 **[`docs/releases/NEXT_STEPS.md`](NEXT_STEPS.md)** - Complete guide to what to do next

Also see [`docs/ROADMAP.md`](../ROADMAP.md) for planned features in version 1.2.0 and beyond.

## Contributors

- Ben Lenzen (@bplenzen)

---

**Philosophy:** This release embodies the Morgan Bowl project ethos: *"teach modern DataOps while providing something useful, take it slow, do it right."* Each fix was implemented carefully with tests and educational documentation.
