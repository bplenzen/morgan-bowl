# Fix Critical Bug: Risk Tier Naming Mismatch

## Problem

The risk tier definitions are inconsistent between two files:

**int_player_risk_factors.sql** (lines 174-182) defines:

- `LOW_RISK` (>= 0.90)
- `MODERATE_RISK` (>= 0.80)
- `HIGH_RISK` (>= 0.70)
- `VERY_HIGH_RISK` (< 0.70)

**fct_draft_performance.sql** references `VERY_LOW_RISK` in 12+ places (lines 326, 331, 339, 369, 421, etc.), which doesn't exist!

Examples:

```sql
when risk_tier = 'VERY_LOW_RISK'  -- ❌ This tier doesn't exist!
    and draft_day_opportunity_cost >= 0
    then 'A+ (Elite & Reliable)'
```

## Impact

All draft grade logic checking for "VERY_LOW_RISK" players fails to match anyone, breaking the A+/A grading system for highly reliable players. No one can get the top "Elite & Reliable" grades.

## Required Fix

Add a `VERY_LOW_RISK` tier to `int_player_risk_factors.sql` for the most reliable players (composite_risk_factor >= 0.95).

## Solution

In `dbt/models/intermediate/int_player_risk_factors.sql`, update the risk_tier CASE statement (around line 174-182):

```sql
case
    when composite_risk_factor >= 0.95 then 'VERY_LOW_RISK'  -- NEW: Top 5% most reliable
    when composite_risk_factor >= 0.90 then 'LOW_RISK'
    when composite_risk_factor >= 0.80 then 'MODERATE_RISK'
    when composite_risk_factor >= 0.70 then 'HIGH_RISK'
    else 'VERY_HIGH_RISK'
end as risk_tier
```

## Task

1. Read `dbt/models/intermediate/int_player_risk_factors.sql`
2. Find the `risk_tier` CASE statement (around line 174-182)
3. Add the `VERY_LOW_RISK` tier at the top (>= 0.95)
4. Adjust the `LOW_RISK` threshold to >= 0.90 (keep existing threshold)
5. Run DBT: `cd dbt && poetry run dbt build --select int_player_risk_factors fct_draft_performance`
6. Verify some players now have VERY_LOW_RISK tier

## Completion Criteria

- [ ] VERY_LOW_RISK tier exists in int_player_risk_factors.sql
- [ ] At least some players are classified as VERY_LOW_RISK (the most reliable ones)
- [ ] Draft grades now properly award A+ grades to "Elite & Reliable" players
- [ ] All DBT tests pass

## Validation Query

After fixing, run this to verify the tier distribution:

```sql
SELECT
    risk_tier,
    COUNT(*) as player_count,
    ROUND(AVG(composite_risk_factor), 3) as avg_risk_factor
FROM main_analytics.fct_draft_performance
WHERE games_played >= 5
GROUP BY risk_tier
ORDER BY avg_risk_factor DESC;
```

Expected: You should see VERY_LOW_RISK tier with composite_risk_factor >= 0.95.

---

**After completing this task:**

1. Mark #2 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 2` (or manually update)
3. Move to prompt #3
