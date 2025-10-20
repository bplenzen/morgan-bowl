-- Test that VOR confidence intervals are properly ordered
-- Lower bound ≤ Point estimate ≤ Upper bound

select
    player_id,
    player_name,
    risk_adjusted_scarcity_vor as point_estimate,
    risk_adjusted_vor_lower_bound as lower_bound,
    risk_adjusted_vor_upper_bound as upper_bound
from {{ ref('int_player_risk_factors') }}
where
    -- Only test players with actual VOR
    risk_adjusted_scarcity_vor is not null
    and games_played > 0
    -- Check for ordering violations
    and (
        risk_adjusted_vor_lower_bound > risk_adjusted_scarcity_vor
        or risk_adjusted_scarcity_vor > risk_adjusted_vor_upper_bound
    )
-- Should return 0 rows (no violations)
