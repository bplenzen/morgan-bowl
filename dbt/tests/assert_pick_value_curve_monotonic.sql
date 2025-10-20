-- Test that pick-value curve expectations are reasonable
-- Expected VOR should decrease as pick number increases (generally)

with pick_value_trends as (
    select
        pick_no,
        round,
        expected_vor_at_pick,
        lag(expected_vor_at_pick) over (order by pick_no) as prev_pick_vor,
        expected_vor_at_pick - lag(expected_vor_at_pick) over (order by pick_no) as vor_change
    from {{ ref('int_expected_value_by_pick') }}
    where pick_no between 1 and 120  -- Focus on typical draft range
),

unreasonable_increases as (
    select *
    from pick_value_trends
    where
        -- Flag if VOR increases by more than 20 between consecutive picks
        -- (Some variation is normal due to position scarcity, but not huge jumps)
        vor_change > 20
)

select
    pick_no,
    round,
    expected_vor_at_pick,
    prev_pick_vor,
    vor_change
from unreasonable_increases
-- Should return 0 rows (curve should be generally decreasing)
