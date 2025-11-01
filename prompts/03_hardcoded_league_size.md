# Fix Critical Bug: Hardcoded League Size Assumption

## Problem

The file `dbt/models/intermediate/int_expected_value_by_pick.sql` hardcodes league size at 10 teams per round (line 136):

```sql
ceil(row_number() over (order by preseason_adp) / 10.0) as round
```

However, according to `CLAUDE.md`, this is a **12-team league**. This makes all pick-value curve calculations incorrect.

## Impact

- Round numbers are wrong (pick 25 is calculated as round 3 instead of round 3)
- Pick-value curve tiers are misaligned
- "Expected VOR at pick" calculations are off
- Draft grade context is incorrect (round-based thresholds are wrong)

## Required Fix

Replace the hardcoded `10.0` with dynamic league size from the `stg_league` table.

## Solution

In `dbt/models/intermediate/int_expected_value_by_pick.sql`, update line 136:

```sql
-- Before (WRONG):
ceil(row_number() over (order by preseason_adp) / 10.0) as round

-- After (CORRECT):
ceil(row_number() over (order by preseason_adp) /
    (select total_rosters from {{ ref('stg_league') }})
) as round
```

## Task

1. Read `dbt/models/intermediate/int_expected_value_by_pick.sql`
2. Locate line 136 (in the `draft_pick_mapping` CTE)
3. Replace `/ 10.0` with `/ (select total_rosters from {{ ref('stg_league') }})`
4. Run DBT: `cd dbt && poetry run dbt build --select int_expected_value_by_pick`
5. Verify downstream models: `poetry run dbt build --select fct_draft_performance`
6. Run all tests: `poetry run dbt test`

## Completion Criteria

- [ ] League size is dynamically loaded from stg_league
- [ ] Round numbers are correct for 12-team league (pick 1-12 = round 1, pick 13-24 = round 2, etc.)
- [ ] All DBT tests pass
- [ ] Pick-value curve shows correct round assignments

## Validation Query

After fixing, verify round assignments are correct:

```sql
SELECT
    pick_no,
    round,
    expected_vor_at_pick
FROM main_analytics.int_expected_value_by_pick
WHERE pick_no IN (1, 12, 13, 24, 25, 36)
ORDER BY pick_no;
```

Expected results for 12-team league:

- Pick 1-12: round = 1
- Pick 13-24: round = 2
- Pick 25-36: round = 3

---

**After completing this task:**

1. Mark #3 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 3` (or manually update)
3. Move to prompt #4
