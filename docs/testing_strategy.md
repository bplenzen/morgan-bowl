# Data Quality Testing Strategy 🧪

Comprehensive testing to ensure your data is correct at every stage.

## 🎯 Testing Philosophy

**3-Layer Defense:**

1. **Source Truth Tests** - Validate against Sleeper API directly
2. **Ingestion Tests** - Ensure data loaded correctly into DuckDB
3. **Transformation Tests** - DBT tests on models

## 📊 Current Test Coverage

### ✅ What You Already Have

**DBT Tests** (17 total):

- Not null checks on key fields
- Uniqueness constraints
- Custom business logic (2 rosters per matchup)
- Referential integrity

**Python Tests** (23 total):

- Unit tests for ingestion logic
- SQL injection protection
- Error handling
- Data persistence

### ⚠️ What's Missing

**Source of Truth Validation:**

- Compare ingested data vs live API
- Validate point totals match
- Check for data drift over time
- Verify all weeks are present

## 🔧 Recommended Test Structure

```
tests/
├── integration/           # NEW - Test against live API
│   ├── test_api_parity.py          # Compare DB vs API
│   ├── test_point_accuracy.py      # Verify scoring matches
│   └── test_completeness.py        # Check all data present
├── data_quality/          # NEW - Data validation
│   ├── test_weekly_checks.py       # Week-specific validations
│   └── test_consistency.py         # Cross-week consistency
└── ingestion/            # EXISTING
    └── test_*.py         # Unit tests
```

## 🎯 Priority Tests to Add

### Level 1: Critical (Must Have)

**Test 1: API Parity Check**

```python
# Compare week's points in DB vs Sleeper API
def test_week_points_match_api(week):
    """Ensure points in database exactly match Sleeper API"""
    # Fetch from API
    # Fetch from DB
    # Assert they match
```

**Test 2: Completeness Check**

```python
def test_all_rosters_have_data(week):
    """Verify all 12 rosters have matchup data for the week"""
    # Should have exactly 12 rosters
    # Each roster should have exactly 1 matchup per week
```

**Test 3: Point Total Validation**

```python
def test_matchup_points_are_reasonable(week):
    """Flag if points are suspiciously high/low"""
    # 0 < points < 250 (reasonable bounds)
    # No negative scores
    # No null values
```

### Level 2: Important (Should Have)

**Test 4: Historical Consistency**

```python
def test_historical_data_unchanged(week):
    """Ensure past weeks' data doesn't change"""
    # Store checksums of past weeks
    # Verify they don't change on re-ingestion
```

**Test 5: Standings Math**

```python
def test_standings_calculations():
    """Verify wins/losses add up correctly"""
    # Sum of wins across league = sum of losses
    # Win % calculated correctly
    # Points for/against match matchup data
```

### Level 3: Nice to Have

**Test 6: Data Freshness**

```python
def test_data_is_current():
    """Alert if data is stale"""
    # Check last ingested week vs current NFL week
    # Flag if more than 1 week behind
```

## 🚀 Implementation Plan

I can create these tests in phases:

### Phase 1: API Validation Tests (30 min)

- Create `tests/integration/test_api_parity.py`
- Test that compares DB vs live API for a given week
- Run as part of CI/CD pipeline

### Phase 2: Completeness Tests (20 min)

- Add tests for roster count, week presence
- Validate no missing data

### Phase 3: DBT Great Expectations (Advanced)

- Use DBT packages for statistical tests
- Validate distributions, ranges, patterns

## 📝 Example Test Implementation

Here's what a source-of-truth test would look like:

```python
def test_week_6_points_match_sleeper_api():
    """
    Compare week 6 points in our DB vs Sleeper API.
    This is the SOURCE OF TRUTH test.
    """
    import httpx
    import duckdb

    # Fetch from Sleeper API (source of truth)
    response = httpx.get(
        f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/6"
    )
    api_data = {m['roster_id']: m['points'] for m in response.json()}

    # Fetch from our database
    conn = duckdb.connect('data/warehouse.duckdb')
    db_data = conn.execute("""
        SELECT roster_id, points
        FROM staging.matchups_week_06
    """).fetchall()
    db_dict = {roster_id: points for roster_id, points in db_data}

    # Compare
    for roster_id in api_data:
        assert roster_id in db_dict, f"Missing roster {roster_id}"
        assert abs(api_data[roster_id] - db_dict[roster_id]) < 0.01, \
            f"Points mismatch for roster {roster_id}: API={api_data[roster_id]}, DB={db_dict[roster_id]}"
```

## ⚙️ Running Tests

```bash
# All tests
poetry run pytest tests/ -v

# Only integration tests (API validation)
poetry run pytest tests/integration/ -v

# Only data quality tests
poetry run pytest tests/data_quality/ -v

# Specific test
poetry run pytest tests/integration/test_api_parity.py::test_week_6_points_match_sleeper_api -v
```

## 🔄 CI/CD Integration

Your `.gitlab-ci.yml` already runs tests, but we can add:

```yaml
test:api_parity:
  stage: test
  script:
    - echo "🔍 Validating data against Sleeper API..."
    - poetry run pytest tests/integration/ -v --junitxml=api_tests.xml
  artifacts:
    reports:
      junit: api_tests.xml
  # Only run on scheduled pipelines (after ingestion)
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
```

## 📊 Test Reporting

**Option 1: Pytest Reports** (what you have now)

- Simple pass/fail
- JUnit XML for GitLab

**Option 2: Great Expectations** (Advanced)

- Statistical data validation
- Data profiling
- Nice HTML reports

**Option 3: DBT Tests + Docs** (what you have)

- Test results in `dbt/target/`
- Documentation site

## 🎯 What Do You Want?

I can build:

**A) Quick Win (30 min)**

- API parity tests for weeks 1-6
- Completeness checks
- Add to your existing pytest suite

**B) Comprehensive (1-2 hours)**

- All critical + important tests
- DBT Great Expectations integration
- Full CI/CD integration
- Test documentation

**C) Just the Plan (now)**

- This document
- You implement as needed

Which approach sounds best for your learning goals?
