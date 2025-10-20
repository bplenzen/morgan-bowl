# Weekly Data Update Process

## Overview

The Morgan Bowl analytics system automatically refreshes with new weekly data. This document explains what gets updated and how to ensure data stays fresh.

## Automated Weekly Updates

### What Runs Weekly

The `scripts/weekly_ingestion.py` script automatically:

1. **Detects current NFL week** from Sleeper API
2. **Checks which weeks are already ingested**
3. **Ingests missing weeks** (matchups, player stats, rosters)
4. **Runs all dbt models** to refresh analytics

### What Gets Updated

When new weekly data is ingested, these models automatically refresh:

#### Staging Models (Raw Data Views)

- `stg_player_stats` - NEW week's player performance
- `stg_matchups_week_N` - NEW week's matchup results

#### Intermediate Models (Calculations)

- `int_player_weekly_variance` - **Updates with new week's variance**
- `int_current_player_rankings` - **Recalculates with new totals**
- `int_player_risk_factors` - **Recalculates uncertainty with new data**
- `int_expected_value_by_pick` - **FROZEN** (only preseason data)
- `int_draft_day_baseline` - **FROZEN** (only preseason data)

#### Fact Tables (Final Analytics)

- `fct_draft_performance` - **Refreshes grades with new VOR/uncertainty**
- `fct_advanced_luck` - **Recalculates expected wins with new week**
- `fct_weekly_performance` - **Adds new week's performance**

### Frozen vs Dynamic Data

**✅ FROZEN (Never Changes)**

- Draft day baseline replacement levels
- Preseason ADP rankings
- Expected value by pick curve
- Draft day parameters (QB12, RB28, WR32, TE12)

**🔄 DYNAMIC (Updates Weekly)**

- Current player rankings
- Weekly variance & consistency tiers
- Risk-adjusted VOR **with confidence intervals**
- Draft grades **with uncertainty ranges**
- Expected wins
- Schedule luck

## How to Run Weekly Updates

### Option 1: Automatic (Recommended)

```bash
# Run the automated weekly ingestion script
cd /Users/benlenzen/Codebase/morgan-bowl
poetry run python scripts/weekly_ingestion.py
```

**What it does:**

1. Checks Sleeper API for current week
2. Ingests any missing weeks since last run
3. Runs `dbt run` to rebuild all models
4. Shows success/failure for each step

### Option 2: Manual (If you know the week)

```bash
# Ingest specific week
poetry run python -m src.ingestion.cli --week 8

# Rebuild models
cd dbt && poetry run dbt run

# Run tests
poetry run dbt test
```

### Option 3: Full Rebuild

If something seems off, you can rebuild everything:

```bash
cd dbt

# Rebuild all models from scratch
poetry run dbt run --full-refresh

# Run all tests
poetry run dbt test
```

## What to Monitor

### After Each Weekly Update

Check these metrics to ensure data quality:

```sql
-- Check latest week ingested
SELECT MAX(week) as latest_week
FROM staging.stg_player_stats;

-- Verify draft analysis is fresh
SELECT
    player_name,
    grade_score,
    grade_score_uncertainty,
    vor_uncertainty_range,
    games_played
FROM main_analytics.fct_draft_performance
WHERE pick_no <= 30
ORDER BY pick_no;

-- Check uncertainty ranges are reasonable
SELECT
    COUNT(*) as total_players,
    COUNT(CASE WHEN vor_uncertainty_range IS NOT NULL THEN 1 END) as with_uncertainty,
    AVG(vor_uncertainty_range) as avg_uncertainty
FROM main_analytics.int_player_risk_factors
WHERE games_played >= 2;  -- Need 2+ games for variance
```

### Expected Behavior

**Week 1:**

- Most players have NULL uncertainty (need 2+ games)
- Grade confidence intervals = point estimate

**Week 2+:**

- Uncertainty ranges start appearing
- Players with high weekly volatility get wide confidence intervals
- Consistent players get narrow confidence intervals

**Week 10+:**

- Large sample sizes
- Confidence intervals stabilize
- High-variance players clearly identified

## Uncertainty Quantification Notes

### How Uncertainty Works

1. **Weekly Variance** is calculated from actual game-by-game performance
2. **VOR Confidence Intervals** use ±1 standard deviation of weekly points
3. **Grade Confidence Intervals** propagate VOR uncertainty through grading formula

### What Changes Each Week

- **Point estimates** (VOR, grades) update with new totals
- **Confidence intervals** get narrower as sample size increases
- **Uncertainty ranges** shrink as season progresses (more data = more certainty)

### Players with Missing Uncertainty

These players will have NULL uncertainty bounds:

- **1 game played** - can't calculate stddev
- **Injured players** - no variance data
- **Consistent zeros** - no meaningful variance

For these players, the grade confidence interval defaults to the point estimate (lower = upper = point).

## Troubleshooting

### "Database locked" error

- Close any open connections to `data/warehouse.duckdb`
- Kill any hanging dbt processes

### Models not updating

```bash
# Force full refresh
cd dbt && poetry run dbt run --full-refresh --select +fct_draft_performance
```

### Tests failing after update

```bash
# Run specific failing test with details
poetry run dbt test --select assert_vor_confidence_intervals_ordered --store-failures

# Query the failure details
poetry run duckdb ../data/warehouse.duckdb -c "SELECT * FROM main_dbt_test__audit.assert_vor_confidence_intervals_ordered"
```

### Uncertainty seems wrong

```bash
# Check sample player
poetry run duckdb data/warehouse.duckdb -c "
SELECT
    player_name,
    games_played,
    risk_adjusted_scarcity_vor,
    risk_adjusted_vor_lower_bound,
    risk_adjusted_vor_upper_bound,
    vor_uncertainty_range,
    grade_score,
    grade_score_lower_bound,
    grade_score_upper_bound
FROM main_analytics.fct_draft_performance
WHERE player_name = 'Christian McCaffrey';
"
```

## Summary

**Key Takeaway:** The weekly ingestion script automatically keeps your data fresh. Just run it after each NFL week, and all models (including uncertainty quantification) will update automatically!

The new uncertainty metrics (confidence intervals, grade ranges) get **more accurate** as the season progresses since they're based on actual weekly performance variance.
