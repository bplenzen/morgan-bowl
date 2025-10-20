-- Test that VOR uncertainty ranges are reasonable (within 5 sigma)
-- Prevents statistical anomalies or calculation errors
-- Note: Some low-VOR players can have high relative uncertainty (that's valid!)

select
    player_id,
    player_name,
    risk_adjusted_scarcity_vor as vor,
    vor_uncertainty_range,
    vor_coefficient_of_variation as vor_cv,
    vor_uncertainty_range / nullif(abs(risk_adjusted_scarcity_vor), 0) as uncertainty_ratio
from {{ ref('int_player_risk_factors') }}
where
    games_played > 0
    and risk_adjusted_scarcity_vor is not null
    and vor_uncertainty_range is not null
    -- Flag if uncertainty is > 5x the point estimate (5 sigma rule - more lenient)
    -- AND the absolute VOR is > 10 (to avoid flagging low-value volatile players)
    and vor_uncertainty_range > abs(risk_adjusted_scarcity_vor) * 5
    and abs(risk_adjusted_scarcity_vor) > 10
-- Should return 0 rows (no extreme outliers among meaningful players)
