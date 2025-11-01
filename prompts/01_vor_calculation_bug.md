# Fix Critical Bug: VOR Calculation Uses ADP as PPG

## Problem

The file `dbt/models/intermediate/int_player_risk_factors.sql` has a severe bug at lines 138-141 where it uses `replacement_adp` (draft pick number) as if it were points per game (PPG).

Current broken code:

```sql
(cr.points_per_game - (
    select replacement_adp from draft_day_baseline
    where position = prc.position limit 1
) / 17.0  -- ❌ WRONG: ADP is draft position, not PPG!
) * prc.games_played
```

This makes no sense: Jordan Love's ADP of 96 divided by 17 = 5.6 "PPG" which is absurdly low.

## Impact

All VOR calculations, draft grades, and risk-adjusted metrics are fundamentally broken throughout the entire application. This is the most critical bug in the codebase.

## Required Fix

Replace the ADP-based calculation with actual replacement-level PPG values by joining to current season data.

The replacement levels are already defined correctly in `int_draft_day_baseline.sql`:

- QB12 (Jordan Love)
- RB28 (Najee Harris)
- WR32 (Jordan Addison)
- TE12 (Cole Kmet)

We need to get their actual current PPG, not their draft position.

## Solution Approach

Update `int_player_risk_factors.sql` to join to `int_current_player_rankings` and fetch the actual PPG for the replacement-level player at each position.

Replace the calculation at line 138-141 with:

```sql
-- Get replacement PPG from actual current rankings
case
    when cr.points_per_game is not null
        then
            (cr.points_per_game - (
                select points_per_game
                from {{ ref('int_current_player_rankings') }}
                where position = prc.position
                  and current_rank_position = (
                      select replacement_rank
                      from {{ ref('int_draft_day_baseline') }}
                      where position = prc.position
                  )
            )) * prc.games_played
    else 0
end as base_vor_estimate
```

## Task

1. Read `dbt/models/intermediate/int_player_risk_factors.sql`
2. Locate the bug around lines 132-143 (search for "replacement_adp / 17.0")
3. Replace the entire `base_vor_estimate` calculation with the corrected version above
4. Run DBT to test: `cd dbt && poetry run dbt build --select int_player_risk_factors`
5. Verify downstream models work: `poetry run dbt build --select fct_draft_performance`
6. Run all tests: `poetry run dbt test`

## Completion Criteria

- [ ] VOR calculation uses actual PPG from current rankings, not ADP
- [ ] All DBT tests pass
- [ ] Draft grades show reasonable values (check a few players in the dashboard)
- [ ] No compilation errors in downstream models

## Validation Query

After fixing, run this to verify VOR values are reasonable:

```sql
-- Expected: QB should have lower VOR than RB/TE due to positional scarcity
SELECT
    position,
    ROUND(AVG(risk_adjusted_scarcity_vor), 1) as avg_vor,
    ROUND(MIN(risk_adjusted_scarcity_vor), 1) as min_vor,
    ROUND(MAX(risk_adjusted_scarcity_vor), 1) as max_vor
FROM main_analytics.fct_draft_performance
WHERE games_played >= 5
GROUP BY position
ORDER BY avg_vor DESC;
```

Expected results: TE/RB should have highest avg VOR, QB should be lower (due to scarcity multipliers).

---

**After completing this task:**

1. Mark #1 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 1` (or manually update)
3. Move to prompt #2
