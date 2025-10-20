{{ config(materialized='table') }}

/*
Player Risk Factors - Multiplicative Model

Calculates risk adjustment factors using MULTIPLICATIVE approach (not averaged).
This follows the peer review recommendation:

Risk Factor = Availability Factor × Volatility Factor × Position Prior

Where:
- Availability Factor = games_played / games_expected (0.0-1.0)
- Volatility Factor = f(CV) mapped to [0.7-1.0] range
- Position Prior = fragility baseline (RB=0.85, WR=0.95, TE=0.90, QB=1.00)

The final Risk Factor is then applied to VOR:
Risk-Adjusted VOR = VOR × Risk Factor

This properly compounds risks rather than averaging them.
Example: A fragile RB (0.85) who missed games (0.80) is much riskier than averaging suggests.
*/

with current_rankings as (
    select * from {{ ref('int_current_player_rankings') }}
),

weekly_variance as (
    select * from {{ ref('int_player_weekly_variance') }}
),

draft_day_baseline as (
    select * from {{ ref('int_draft_day_baseline') }}
),

-- Get expected games (17 game season)
season_info as (
    select 17 as expected_games
),

-- Position-specific fragility priors (from parameter file)
-- These represent the baseline injury/availability risk by position
position_priors as (
    select
        'QB' as position,
        1.00 as position_fragility_factor,
        'Most durable' as fragility_notes
    union all
    select
        'WR' as position,
        0.95 as position_fragility_factor,
        'Moderate risk'
    union all
    select
        'TE' as position,
        0.90 as position_fragility_factor,
        'Moderate-high risk'
    union all
    select
        'RB' as position,
        0.85 as position_fragility_factor,
        'Highest injury risk'
),

-- Calculate individual risk factors for each player
player_risk_components as (
    select
        cr.player_id,
        cr.player_name,
        cr.position,
        cr.games_played,
        cr.points_per_game,
        cr.total_points,

        -- Availability Factor: What % of expected games did they play?
        -- Range: 0.0 (missed all games) to 1.0 (played all games)
        pp.position_fragility_factor,

        -- Volatility Factor: Based on coefficient of variation
        -- Map CV to risk factor range [0.7, 1.0]
        -- Lower CV = more consistent = factor closer to 1.0
        -- Higher CV = more volatile = factor closer to 0.7
        pp.fragility_notes,

        -- Position Fragility Prior (from frozen parameters)
        wv.coefficient_of_variation,
        wv.boom_rate_pct,

        -- Raw metrics for reference
        wv.bust_rate_pct,
        si.expected_games,
        round(
            cast(cr.games_played as decimal) / si.expected_games,
            3
        ) as availability_factor,
        case
            when wv.coefficient_of_variation is null then 1.0
            -- Very consistent
            when wv.coefficient_of_variation <= 0.20 then 1.00
            when wv.coefficient_of_variation <= 0.30 then 0.95  -- Consistent
            when wv.coefficient_of_variation <= 0.40 then 0.90  -- Moderate
            when wv.coefficient_of_variation <= 0.50 then 0.85  -- Volatile
            when wv.coefficient_of_variation <= 0.60 then 0.80  -- Very volatile
            -- Extremely volatile
            when wv.coefficient_of_variation <= 0.70 then 0.75
            else 0.70  -- Wildly inconsistent
        end as volatility_factor

    from current_rankings as cr
    cross join season_info as si
    left join weekly_variance as wv
        on cr.player_id = wv.player_id
    left join position_priors as pp
        on cr.position = pp.position
    where cr.position in ('QB', 'RB', 'WR', 'TE')
),

-- Calculate MULTIPLICATIVE risk factor and apply to VOR
risk_adjusted_vor as (
    select
        prc.*,

        -- MULTIPLICATIVE RISK FACTOR (not averaged!)
        -- This properly compounds the risks
        round(
            prc.availability_factor
            * prc.volatility_factor
            * prc.position_fragility_factor,
            3
        ) as composite_risk_factor,

        -- Calculate base VOR (current season vs draft-day baseline)
        case
            when prc.points_per_game is not null
                then
                    (
                        prc.points_per_game
                        - (
                            select replacement_adp from draft_day_baseline
                            where position = prc.position limit 1
                        ) / 17.0  -- Rough PPG estimate from ADP
                    ) * prc.games_played
            else 0
        end as base_vor_estimate,

        -- Get scarcity multiplier from frozen baseline
        (
            select vor_multiplier from draft_day_baseline
            where position = prc.position limit 1
        ) as scarcity_multiplier

    from player_risk_components as prc
),

-- Apply risk adjustment to VOR
final_risk_adjusted as (
    select
        *,

        -- Risk-Adjusted VOR = Base VOR × Scarcity × Risk Factor
        round(
            base_vor_estimate * scarcity_multiplier * composite_risk_factor,
            2
        ) as risk_adjusted_scarcity_vor,

        -- Show how much VOR was reduced by risk
        round(
            base_vor_estimate
            * scarcity_multiplier
            * (1.0 - composite_risk_factor),
            2
        ) as vor_lost_to_risk,

        -- Risk tier categorization
        case
            -- Very reliable
            when composite_risk_factor >= 0.90 then 'LOW_RISK'
            -- Some concerns
            when composite_risk_factor >= 0.80 then 'MODERATE_RISK'
            -- Significant risk
            when composite_risk_factor >= 0.70 then 'HIGH_RISK'
            else 'VERY_HIGH_RISK'  -- Major red flags
        end as risk_tier,

        -- Identify primary risk driver
        case
            -- Missing games
            when availability_factor < 0.80 then 'AVAILABILITY'
            when volatility_factor < 0.85 then 'VOLATILITY'      -- Inconsistent
            -- Fragile position
            when position_fragility_factor < 0.90 then 'POSITION'
            else 'MINIMAL_RISK'
        end as primary_risk_driver

    from risk_adjusted_vor
)

select * from final_risk_adjusted
order by risk_adjusted_scarcity_vor desc
