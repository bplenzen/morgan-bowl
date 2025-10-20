/*
Validation: Risk-Adjusted VOR calculations
Ensures risk penalties are reasonable and risk-adjusted VOR makes sense
*/

with risk_checks as (
    select
        player_id,
        player_name,
        position,
        vor,
        risk_adjusted_vor,
        risk_adjusted_scarcity_vor,
        composite_risk_penalty,
        games_played,
        coefficient_of_variation
    from {{ ref('int_risk_adjusted_vor') }}
)

select *
from risk_checks
where
    -- Risk penalty should be between 0% and 50%
    composite_risk_penalty < 0
    or composite_risk_penalty > 0.50

    -- Risk-adjusted VOR should have smaller absolute value than original
    -- (risk penalty reduces the magnitude, whether positive or negative)
    or abs(risk_adjusted_vor) > abs(vor) + 0.1  -- Small tolerance for rounding

    -- Coefficient of variation should be non-negative
    or coefficient_of_variation < 0
