/*
Data Validation Test: Variance Metrics Valid
Ensures weekly variance metrics are correctly calculated and within valid ranges:
- Coefficient of variation should be non-negative
- Boom/bust rates should be between 0-100%
- Floor should be <= Ceiling
- Players with games_played but no variance data indicates data quality issue
  (but allow nulls - could be injured mid-season or single week played)
*/

with validation_failures as (
    select
        player_name,
        position,
        games_played,
        coefficient_of_variation,
        boom_rate_pct,
        bust_rate_pct,
        floor_10th_percentile,
        ceiling_90th_percentile,
        case
            when coefficient_of_variation < 0 then 'Negative CV'
            when boom_rate_pct < 0 or boom_rate_pct > 100 then 'Invalid boom rate'
            when bust_rate_pct < 0 or bust_rate_pct > 100 then 'Invalid bust rate'
            when floor_10th_percentile is not null
                 and ceiling_90th_percentile is not null
                 and floor_10th_percentile > ceiling_90th_percentile then 'Floor > Ceiling'
        end as failure_reason
    from {{ ref('fct_draft_performance') }}
    where position not in ('DEF', 'K')  -- Exclude positions without individual stats
)

select *
from validation_failures
where failure_reason is not null
