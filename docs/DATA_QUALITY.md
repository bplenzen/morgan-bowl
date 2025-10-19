# Data Quality & Testing 🧪

## ✅ What You Now Have

**65 Total Tests** protecting your data pipeline:

### 1. Unit Tests (23 tests)

**Location:** `tests/ingestion/`

- SQL injection protection
- Error handling
- Data persistence logic
- Configuration management

### 2. DBT Tests (17 tests)

**Location:** `dbt/tests/` and model YAML files

- Not null constraints
- Uniqueness checks
- Referential integrity
- Business logic (2 rosters per matchup)

### 3. Integration Tests (42 tests) ⭐ NEW

**Location:** `tests/integration/test_api_parity.py`

**SOURCE OF TRUTH validation** - compares DB vs live Sleeper API:

#### API Parity (12 tests)

- ✅ Matchup points match API exactly (all 6 weeks)
- ✅ Matchup IDs match API (correct opponent pairings)

#### Data Completeness (16 tests)

- ✅ All weeks ingested (1-6)
- ✅ All 12 rosters present each week
- ✅ Exactly 6 matchups per week
- ✅ League info matches
- ✅ All users present

#### Data Quality (14 tests)

- ✅ Points are reasonable (0-300 range)
- ✅ No negative/null scores
- ✅ Each matchup has exactly 2 teams
- ✅ Wins = Losses across league
- ✅ Win percentages calculated correctly

## 🎯 Testing Philosophy

**3-Layer Defense:**

```
┌─────────────────────────────────────────┐
│  Layer 1: API Parity Tests (42)         │  ← Validates against source of truth
│  "Is our data exactly what API says?"   │
├─────────────────────────────────────────┤
│  Layer 2: DBT Tests (17)                │  ← Validates transformations
│  "Are our models correct?"              │
├─────────────────────────────────────────┤
│  Layer 3: Unit Tests (23)               │  ← Validates code logic
│  "Does our code work?"                  │
└─────────────────────────────────────────┘
```

## 🔄 When Tests Run

### Locally (During Development)

```bash
# All tests
poetry run pytest tests/ -v

# Only API validation
poetry run pytest tests/integration/ -v

# Only unit tests
poetry run pytest tests/ingestion/ -v

# DBT tests
cd dbt && poetry run dbt test
```

### In CI/CD (GitLab)

Automatically runs on:

- ✅ Scheduled pipelines (every Tuesday)
- ✅ Manual pipeline runs
- ✅ Pull requests (future)

Pipeline stages:

1. **Ingest** - Pull data from Sleeper
2. **Build** - Run DBT transformations
3. **Test** - Validate everything:
   - DBT tests
   - Unit tests
   - **API parity tests** ← Blocks bad data!

## 🚨 What Happens if Tests Fail?

### API Parity Test Failure

**This is CRITICAL** - means your data doesn't match Sleeper!

Example failure:

```
Week 5, Roster 3: API=132.5, DB=130.2
AssertionError: Points don't match!
```

**What to do:**

1. Check if Sleeper had a stat correction
2. Re-run ingestion for that week
3. Investigate if there's a bug in ingestion logic

### DBT Test Failure

**Business logic violated**

Example:

```
test not_null_fct_matchups_roster_id failed
```

**What to do:**

1. Check DBT logs: `dbt/logs/dbt.log`
2. Run failing test locally: `dbt test --select <test_name>`
3. Fix the model or data issue

### Unit Test Failure

**Code regression**

**What to do:**

1. Review the PR/commit that broke it
2. Fix the code
3. Add test to prevent regression

## 📊 Test Coverage Report

Run this to see coverage:

```bash
poetry run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## 🎓 Why This Matters

### Without These Tests

❌ Bad data enters your pipeline
❌ You don't know when something breaks
❌ Historical data could be wrong
❌ Hard to trust your analytics

### With These Tests

✅ **Confidence** - Data matches source of truth
✅ **Early Detection** - Catch issues immediately
✅ **Automation** - No manual checking needed
✅ **Documentation** - Tests show what should be true

## 🏢 Enterprise Patterns You're Learning

1. **Test Pyramid**
   - Many unit tests (fast, cheap)
   - Some integration tests (slower, valuable)
   - Few end-to-end tests (slowest, comprehensive)

2. **Source of Truth Validation**
   - Always compare to authoritative source
   - API parity tests = industry standard

3. **Continuous Integration**
   - Tests run automatically
   - Block bad code/data from merging
   - Fast feedback loop

4. **Data Contracts**
   - Tests define expected data shape
   - Changes require updating tests
   - Prevents breaking downstream consumers

## 📈 Next Level (Optional)

Want even more confidence?

### Statistical Tests (DBT Great Expectations)

```yaml
# In DBT model YAML
tests:
  - dbt_expectations.expect_column_values_to_be_between:
      min_value: 0
      max_value: 300
  - dbt_expectations.expect_column_mean_to_be_between:
      min_value: 80
      max_value: 140
```

### Historical Consistency Checks

```python
def test_past_weeks_unchanged():
    """Ensure historical data doesn't change on re-ingestion"""
    # Store checksums
    # Validate on each run
```

### Data Profiling

```python
# Generate weekly reports:
# - Min/max/avg points per week
# - Distribution of scores
# - Outlier detection
```

## 🎯 Summary

You now have **enterprise-grade data validation**:

- 42 tests that validate against Sleeper API
- Automatic execution in CI/CD
- Pipeline blocks if data is wrong
- Full confidence in your analytics

**Next time you run ingestion, all tests run automatically!**

---

**Questions?** Check test output in GitLab under **Build → Pipelines → [click on run] → Tests tab**
