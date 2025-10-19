# Morgan Bowl - Next Steps & Future Development

**Last Updated**: October 19, 2025  
**Current Version**: v1.1.0 (Universal League Configuration)

This document consolidates all "next steps" from across the project into a single reference.

---

## 🎯 Current Status

**What's Working Now**:
- ✅ v1.0.0: Core pipeline (ingestion, DBT, dashboard, automated runs)
- ✅ v1.0.1: Security fixes, error handling, configuration improvements
- ✅ v1.1.0: Universal league configuration (works with ANY Sleeper league)

**Environment**: Python 3.11.9, Poetry, DuckDB  
**Data**: 2025 season ingested through current week  
**Database**: `data/warehouse.duckdb` (12 users, 12 rosters, matchups, transactions)

---

## 🚀 Quick Start Paths

Choose your adventure based on what you want to do next:

### Path 1: Use Morgan Bowl With Your Own League (15 mins)

**Status**: ✅ READY - v1.1.0 feature complete!

1. Find your Sleeper league ID from URL
2. Update `.env` with your `SLEEPER_LEAGUE_ID`
3. Run `poetry run python -m ingestion.cli`
4. Build analytics: `cd dbt && poetry run dbt build`

**Result**: Your league data analyzed with zero configuration!

See `README.md` → "🌍 Use With ANY Sleeper League" for full instructions.

---

### Path 2: Set Up GitLab Automation (20 mins)

**Status**: ✅ READY - CI/CD pipeline configured

1. Push to GitLab
2. Configure secrets (league ID, season)
3. Create schedule (Tuesday 6 AM)
4. Watch it run automatically

**Result**: Fresh data every week with zero manual work!

See `docs/setup/QUICK_START.md` for step-by-step guide.

---

### Path 3: Explore & Analyze Current Data (15 mins)

**Status**: ✅ READY - Data is ingested

Quick exploration:

```python
import duckdb

conn = duckdb.connect('data/warehouse.duckdb')

# Current standings
standings = conn.execute("""
    SELECT manager_name, wins, losses, points_for, win_pct
    FROM main_analytics.fct_standings
    ORDER BY wins DESC, points_for DESC
""").fetchall()

# Justice record (deserved wins vs actual)
justice = conn.execute("""
    SELECT manager_name, actual_wins, justice_wins, 
           luck_differential, luck_status
    FROM main_analytics.fct_justice_record
    ORDER BY justice_wins DESC
""").fetchall()
```

**Result**: Understand your data structure and start finding insights!

---

### Path 4: Build Advanced Analytics (varies)

**Status**: 🔨 IN DEVELOPMENT - See roadmap below

Choose from v1.2.0+ features (see Roadmap section):
- Injury impact analysis
- Draft performance tracking
- Strength of schedule
- Playoff probability simulator

---

## 📋 Immediate Actions (Choose 1-3)

### 1. **Deploy Dashboard to Production** ⭐ (1 hour)

**Why**: Share insights with your league!

```bash
# Option A: Streamlit Cloud (free, easy)
cd analytics
poetry run streamlit run dashboard.py

# Follow prompts to deploy to streamlit.io

# Option B: Local sharing
poetry run streamlit run dashboard.py --server.port 8501
```

**Impact**: League mates can see their justice records and bad luck!

---

### 2. **Add Data Quality Monitoring** (30 mins)

**Why**: Catch data issues before they become problems

Add to `dbt/tests/`:
- `assert_two_rosters_per_matchup.sql` ✅ (already exists)
- `assert_justice_wins_balanced.sql` ✅ (already exists)
- `assert_unique_fct_matchups.sql` ✅ (already exists)
- New: `assert_points_non_negative.sql`
- New: `assert_no_missing_weeks.sql`

**Impact**: Confidence in data quality

---

### 3. **Document Your Code** (30 mins)

**Why**: Future you will thank you

```python
# Add docstrings to key functions in:
# - src/ingestion/pipeline.py
# - src/ingestion/client.py
# - src/ingestion/persistence.py

def run_ingestion(...) -> dict:
    """Run the ingestion pipeline with retries and validation.
    
    Args:
        config: Ingestion configuration
        client: Sleeper API client
        store: Data store for persistence
        weeks: Sequence of week numbers to ingest
        
    Returns:
        Dict containing run summary with counts and validation results
        
    Raises:
        ValueError: If week validation fails
        Exception: If API calls or data processing fails
    """
```

**Impact**: Better maintainability and onboarding

---

### 4. **Set Up Notifications** (20 mins)

**Why**: Know when your pipeline runs (or fails)

Options:
- **GitLab email notifications** (easiest)
- **Slack webhook** (most professional)
- **Discord webhook** (if your league is there)

See `docs/setup/GITLAB_SETUP.md` → "Optional: Get Notifications"

**Impact**: Peace of mind

---

## 🗺️ Feature Roadmap

### v1.2.0 - Advanced Analytics (Next Release)

**Theme**: Injury impact and draft performance

#### 1. **Injury Impact Analysis** 🚑 [HIGH PRIORITY]

**What**: Quantify how injuries affected each team

New models:
- `stg_player_injuries.sql` - Injury status from Sleeper
- `fct_injury_impact.sql` - Games missed, points lost per team
- `fct_bad_luck_rankings.sql` - "Unluckiest Team" rankings

Metrics:
- Games Missed (total games lost to injury)
- Points Missed (projected points lost)
- Draft Capital Lost (ADP of injured players)
- Injury Severity Score (weighted by player quality)
- Bad Luck Index (composite ranking)

**Impact**: VERY HIGH - Everyone wants to complain about injuries!  
**Effort**: 6-8 hours (new API endpoints, projection math)

See `docs/FEATURE_SPEC_injury_analysis.md` for full spec.

---

#### 2. **Draft Performance Analysis** 📊 [HIGH PRIORITY]

**What**: Compare draft picks to current player performance

New models:
- `stg_draft_picks.sql` - Draft results
- `fct_draft_analysis.sql` - Pick value vs performance
- `fct_draft_grades.sql` - Team draft grades A-F

Metrics:
- Hits vs Misses by round
- Value over expected (VoE)
- Best/Worst picks per team
- Overall draft grade

**Impact**: HIGH - Great for offseason trash talk!  
**Effort**: 4-6 hours

See `docs/FEATURE_SPEC_draft_analysis.md` for full spec.

---

#### 3. **Strength of Schedule Analysis** 📈 [MEDIUM PRIORITY]

**What**: Track opponent difficulty over time

New model: `fct_strength_of_schedule.sql`

Metrics:
- Average opponent win %
- Remaining opponent strength
- Schedule difficulty ranking

**Impact**: Medium - Explains tough/easy schedules  
**Effort**: 2 hours

---

### v2.0.0 - Platform Expansion (Future)

#### 1. **Multi-Platform Support** 🌐

- ESPN Fantasy league import
- Yahoo Fantasy league import
- Unified analytics across platforms

**Impact**: VERY HIGH - Opens to entire fantasy community  
**Effort**: Major (20+ hours)

---

#### 2. **Documentation Consolidation** 📚

**Why**: Currently 260+ markdown linting warnings

Tasks:
- Consolidate scattered docs into organized structure
- Fix all markdown formatting
- Create comprehensive user guide
- Improve API documentation
- Add architecture diagrams

**Impact**: Medium - Better developer experience  
**Effort**: 8-10 hours

---

#### 3. **Advanced Features**

- **Playoff Probability Simulator** - Monte Carlo simulation of playoff scenarios
- **Weekly Email Reports** - Automated reports to league
- **Trade Analyzer** - Evaluate trade fairness
- **Waiver Wire Recommendations** - ML-powered pickup suggestions

---

## 📚 Learning & Improvement

### End-to-End Testing

**Status**: Partial coverage

**Next Steps**:
1. Add integration test: ingestion → DBT → dashboard → report
2. Mock Sleeper API for deterministic tests
3. Add performance benchmarks (ingestion time, DBT build time)

**Files to create**:
- `tests/integration/test_full_pipeline.py`
- `tests/integration/test_dashboard_e2e.py`

---

### Code Quality Improvements

**Status**: Good (Black, isort, Ruff configured)

**Next Steps**:
1. Add type hints to all functions (mypy)
2. Increase test coverage to 90%+ (pytest-cov)
3. Add complexity checks (radon, wily)

**Commands**:

```bash
# Type checking
poetry run mypy src/

# Coverage report
poetry run pytest --cov=src tests/

# Complexity
poetry run radon cc src/
```

---

### Observability Enhancements

**Status**: Basic logging with structlog

**Next Steps**:
1. Add Elementary for DBT test monitoring
2. Capture metrics (ingestion time, row counts, API latency)
3. Create Grafana dashboards (if self-hosting)
4. Set up alerting thresholds

**Tools to explore**:
- Elementary (dbt-native observability)
- Prefect Cloud (free tier)
- DataDog / New Relic (if enterprise)

---

## 🎓 Skills to Practice

Choose based on what you want to learn:

### Data Engineering

- [ ] **Incremental models** - DBT incremental materialization
- [ ] **Snapshots** - Track slowly changing dimensions
- [ ] **Seeds** - Reference data management
- [ ] **Macros** - Reusable SQL logic

### Software Engineering

- [ ] **Design patterns** - Strategy, Factory, Repository
- [ ] **SOLID principles** - Clean architecture
- [ ] **Dependency injection** - Testable components
- [ ] **Event-driven architecture** - Async processing

### DataOps

- [ ] **Feature flags** - Toggle features in production
- [ ] **Blue/green deployments** - Zero-downtime releases
- [ ] **Canary releases** - Gradual rollouts
- [ ] **Observability** - Metrics, logs, traces

---

## 🤔 Decision Points

### Should I...

**...add more DBT models?**  
✅ **YES** if you want more analytics (injury impact, draft analysis)  
❌ **NO** if you're happy with current standings/justice record

**...set up GitLab CI/CD?**  
✅ **YES** if you want automated weekly updates  
❌ **NO** if you prefer manual control

**...deploy a dashboard?**  
✅ **YES** if you want to share with your league  
❌ **NO** if it's just for you (Python queries work fine)

**...add ESPN/Yahoo support?**  
⏳ **WAIT** until v2.0.0 (focus on Sleeper first)

**...refactor all documentation?**  
⏳ **WAIT** until v2.0.0 (defer until feature-complete)

---

## 📞 Getting Help

- **Project docs**: `docs/README.md` - documentation index
- **Setup issues**: `docs/setup/SETUP.md` - troubleshooting
- **DBT help**: `docs/guides/DBT_GUIDE.md` - DBT patterns
- **Roadmap**: `docs/ROADMAP.md` - feature priorities
- **GitLab CI/CD**: `docs/setup/GITLAB_SETUP.md` - automation setup

---

## 🏁 Summary

**You should:**

1. ✅ **Use it** - Run with your league, see the magic!
2. ⚙️ **Automate it** - Set up GitLab schedule (20 mins)
3. 📊 **Share it** - Deploy dashboard for your league
4. 🚀 **Extend it** - Pick a v1.2.0 feature and build it!

**Priority order**:
1. GitLab automation (highest ROI)
2. Dashboard deployment (league visibility)
3. Injury analysis feature (most requested)
4. Documentation improvements (long-term maintainability)

**Remember**: This is a learning project. Pick what excites you and dive deep. There's no wrong choice!

---

**Want guidance?** Ask yourself:

- **"I want to learn X"** → Pick a feature that teaches that skill
- **"I want my league to use this"** → Deploy dashboard + automate updates
- **"I want to practice Y"** → Choose from Skills to Practice section
- **"I'm not sure"** → Start with GitLab automation (universal value)

**Next commit**: Whatever you choose, document it and share your learnings!
