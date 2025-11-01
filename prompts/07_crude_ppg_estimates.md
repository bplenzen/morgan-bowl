# Fix Warning: Pick-Value Curve Uses Crude PPG Estimates

## Problem

The file `dbt/models/intermediate/int_expected_value_by_pick.sql` uses **hardcoded PPG tiers** to estimate player value (lines 64-98):

```sql
when pr.position = 'QB'
    then
        case
            when pr.preseason_rank_position <= 5 then 22.0
            when pr.preseason_rank_position <= 12 then 20.0
            when pr.preseason_rank_position <= 20 then 18.0
            -- etc...
```

These are **rough approximations** that don't reflect actual expert consensus projections.

## Impact

The entire pick-value curve is based on made-up numbers instead of real preseason projections. This undermines:

- "Expected VOR at pick" calculations
- Draft grade comparisons
- Value vs expected metrics

## Why This Matters

You're already using preseason ADP (`stg_preseason_rankings`) which is a decent proxy, but **PPG projections** would be much more accurate. ADP tells you draft position; projections tell you expected performance.

## Long-term Solution (Ideal)

Integrate **FantasyPros Consensus Projections API** (free tier: 1000 calls/month).

Benefits:

- Aggregates 100+ expert analysts
- Industry standard for preseason projections
- Free tier is sufficient for weekly updates
- Provides projected points, not just ranks

## Short-term Solution (This Prompt)

Improve the PPG estimates by using **historical average PPG by position rank** from your own data.

### Implementation

Add a new intermediate model: `int_historical_ppg_by_rank.sql`

```sql
{{ config(materialized='table') }}

-- Calculate historical average PPG by position and rank
-- This gives better estimates than hardcoded tiers

with current_rankings as (
    select * from {{ ref('int_current_player_rankings') }}
),

positional_averages as (
    select
        position,
        current_rank_position,
        round(avg(points_per_game), 1) as avg_ppg,
        round(stddev(points_per_game), 1) as stddev_ppg,
        count(*) as sample_size
    from current_rankings
    where games_played >= 8  -- Full season data only
    group by position, current_rank_position
)

select
    position,
    current_rank_position as rank_position,
    avg_ppg as historical_avg_ppg,
    stddev_ppg as historical_stddev_ppg,
    sample_size,

    -- Smoothed estimate (use nearby ranks if sample size is small)
    round(
        avg(avg_ppg) over (
            partition by position
            order by current_rank_position
            rows between 2 preceding and 2 following
        ),
        1
    ) as smoothed_ppg

from positional_averages
order by position, rank_position
```

Then update `int_expected_value_by_pick.sql` to use this instead of hardcoded values:

```sql
-- Replace lines 56-103 with:
preseason_with_projected_ppg as (
    select
        pr.*,
        rl.estimated_replacement_ppg,
        rl.scarcity_multiplier,

        -- Use historical averages instead of hardcoded tiers
        coalesce(
            (
                select smoothed_ppg
                from {{ ref('int_historical_ppg_by_rank') }} hpr
                where hpr.position = pr.position
                  and hpr.rank_position = pr.preseason_rank_position
            ),
            -- Fallback to conservative estimate if no historical data
            case
                when pr.position = 'QB' then 18.0
                when pr.position = 'RB' then 12.0
                when pr.position = 'WR' then 11.0
                when pr.position = 'TE' then 8.0
            end
        ) as projected_ppg

    from preseason_rankings as pr
    left join replacement_levels as rl
        on pr.position = rl.position
)
```

## Task

1. Create new file: `dbt/models/intermediate/int_historical_ppg_by_rank.sql`
2. Copy the SQL from the "Implementation" section above
3. Update `int_expected_value_by_pick.sql` to reference the new model
4. Add schema documentation for the new model
5. Run DBT: `cd dbt && poetry run dbt build --select int_historical_ppg_by_rank int_expected_value_by_pick`
6. Verify the pick-value curve looks more realistic

## Completion Criteria

- [ ] New `int_historical_ppg_by_rank.sql` model exists
- [ ] `int_expected_value_by_pick.sql` uses historical averages instead of hardcoded tiers
- [ ] All DBT tests pass
- [ ] Pick-value curve shows smoother, more realistic VOR expectations

## Validation Query

After fixing, compare old vs new estimates:

```sql
SELECT
    pick_no,
    round,
    expected_vor_at_pick,
    expected_value_tier
FROM main_analytics.int_expected_value_by_pick
WHERE pick_no IN (1, 12, 24, 36, 60, 100)
ORDER BY pick_no;
```

Expected: VOR should decay smoothly (no sudden jumps at arbitrary thresholds).

## Future Enhancement (Optional)

After this fix, consider adding FantasyPros API integration in a future prompt (#16).

---

**After completing this task:**

1. Mark #7 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 7` (or manually update)
3. Move to prompt #8
