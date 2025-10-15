-- Test: Every week should have exactly 6 justice wins and 6 justice losses
-- This ensures our ranking logic is working correctly

with weekly_justice_totals as (
    select
        week,
        sum(case when points_rank <= 6 then 1 else 0 end) as justice_wins,
        sum(case when points_rank > 6 then 1 else 0 end) as justice_losses
    from (
        select
            week,
            roster_id,
            row_number() over (partition by week order by points desc) as points_rank
        from {{ ref('stg_matchups') }}
    )
    group by week
)

-- Test fails if any week doesn't have exactly 6 wins and 6 losses
select
    week,
    justice_wins,
    justice_losses
from weekly_justice_totals
where justice_wins != 6 or justice_losses != 6
