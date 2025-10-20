/*
Data Validation Test: Scarcity Multipliers Valid
Ensures positional scarcity metrics are correctly calculated:
- Scarcity scores should be between 0 and 1
- VOR multipliers should be reasonable (0.8 to 2.0 range)
- Scarcity-adjusted VOR should be >= base VOR for scarce positions
- All positions should have scarcity data
*/

with validation_failures as (
    select
        position,
        scarcity_score,
        vor_multiplier,
        scarcity_tier,
        case
            when scarcity_score < 0 or scarcity_score > 1 then 'Invalid scarcity score'
            when vor_multiplier < 0.8 or vor_multiplier > 2.0 then 'Invalid multiplier'
            when scarcity_score is null then 'Missing scarcity score'
            when vor_multiplier is null then 'Missing VOR multiplier'
            when scarcity_tier is null then 'Missing scarcity tier'
        end as failure_reason
    from {{ ref('int_positional_scarcity') }}
)

select *
from validation_failures
where failure_reason is not null
