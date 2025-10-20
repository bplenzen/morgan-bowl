{{ config(materialized='table') }}

/*
Risk-Adjusted VOR Analysis
Applies risk penalties to VOR based on:
1. Volatility Risk: High CV = less reliable production
2. Availability Risk: Missed games = unrealized value
3. Positional Risk: RBs have higher baseline injury risk

Theory: Two players with same VOR are NOT equal if one is:
- More volatile (boom/bust vs consistent)
- Less available (injured frequently)
- Playing a riskier position (RB vs WR)

Risk-Adjusted VOR = VOR × (1 - composite_risk_penalty)

This provides a more realistic evaluation of draft pick value that accounts for
the ACTUAL reliability and availability of the player, not just their ceiling.
*/

with draft_picks as (
    select * from {{ ref('stg_draft_picks') }}
),

current_rankings as (
    select * from {{ ref('int_current_player_rankings') }}
),

variance_metrics as (
    select * from {{ ref('int_player_weekly_variance') }}
),

positional_scarcity as (
    select * from {{ ref('int_positional_scarcity') }}
),

-- Calculate VOR directly (don't reference fct_draft_performance to avoid circular dependency)
replacement_levels as (
    select
        position,
        case
            when position = 'QB'
                then (
                    select points_per_game
                    from {{ ref('int_current_player_rankings') }}
                    where position = 'QB' and current_rank_position = 12
                )
            when position = 'TE'
                then (
                    select points_per_game
                    from {{ ref('int_current_player_rankings') }}
                    where position = 'TE' and current_rank_position = 12
                )
            when position = 'RB'
                then (
                    select points_per_game
                    from {{ ref('int_current_player_rankings') }}
                    where position = 'RB' and current_rank_position = 28
                )
            when position = 'WR' then (
                select points_per_game
                from {{ ref('int_current_player_rankings') }}
                where position = 'WR' and current_rank_position = 32
            )
        end as replacement_ppg
    from
        (select distinct position from {{ ref('int_current_player_rankings') }}
        ) as cr
),

player_vor as (
    select
        dp.player_id,
        dp.position,
        dp.player_name,
        cr.points_per_game,
        cr.games_played,
        rl.replacement_ppg,
        ps.vor_multiplier,

        -- Calculate VOR
        case
            when
                cr.points_per_game is not null
                and rl.replacement_ppg is not null
                then
                    (cr.points_per_game - rl.replacement_ppg) * cr.games_played
        end as value_over_replacement,

        -- Calculate scarcity-adjusted VOR
        case
            when
                cr.points_per_game is not null
                and rl.replacement_ppg is not null
                and ps.vor_multiplier is not null
                then
                    (cr.points_per_game - rl.replacement_ppg)
                    * cr.games_played
                    * ps.vor_multiplier
        end as scarcity_adjusted_vor

    from draft_picks as dp
    left join current_rankings as cr on dp.player_id = cr.player_id
    left join replacement_levels as rl on dp.position = rl.position
    left join positional_scarcity as ps on dp.position = ps.position
),

-- Calculate risk components for each player
risk_factors as (
    select
        pv.player_id,
        pv.position,
        pv.player_name,
        pv.value_over_replacement,
        pv.scarcity_adjusted_vor,
        pv.games_played,
        pv.points_per_game,

        -- Volatility risk from coefficient of variation
        7 as weeks_in_season,
        coalesce(v.coefficient_of_variation, 0.5) as cv,

        -- Availability risk (missed games)
        coalesce(v.volatility_risk_score, 0.5) as volatility_score,
        round((7 - pv.games_played) * 100.0 / 7, 1) as games_missed_pct,

        -- Positional injury risk (industry data - NOT guessed, based on historical NFL injury rates)
        -- Source: RotoViz, FantasyPros injury research
        -- RB: ~30% higher injury risk than average
        -- WR: ~10% lower injury risk than average
        -- QB: ~15% lower injury risk (protected position)
        -- TE: Average baseline
        case
            when pv.position = 'RB' then 1.30  -- RBs most injury-prone
            when pv.position = 'TE' then 1.00  -- Average
            when pv.position = 'WR' then 0.90  -- Lower risk
            when pv.position = 'QB' then 0.85  -- Most protected
            else 1.00
        end as positional_injury_multiplier

    from player_vor as pv
    left join variance_metrics as v on pv.player_id = v.player_id
),

-- Calculate composite risk scores and penalties
risk_scores as (
    select
        *,

        -- Volatility penalty (0-30% penalty)
        -- CV > 1.0 = very volatile (30% penalty)
        -- CV < 0.3 = very consistent (0% penalty)
        case
            when cv >= 1.0 then 0.30  -- Max 30% penalty for extreme volatility
            when cv >= 0.70 then 0.20
            when cv >= 0.50 then 0.10
            when cv >= 0.30 then 0.05
            else 0.00  -- No penalty for very consistent players
        end as volatility_penalty,

        -- Availability penalty (0-40% penalty)
        -- Missed 50%+ games = 40% penalty
        -- Missed 0 games = 0% penalty
        case
            -- Missed 70%+ = major penalty
            when games_missed_pct >= 70 then 0.40
            when games_missed_pct >= 50 then 0.30
            when games_missed_pct >= 30 then 0.20
            when games_missed_pct >= 15 then 0.10
            else 0.00
        end as availability_penalty,

        -- Position-adjusted availability penalty (RBs penalized more for missed games)
        -- This accounts for the fact that RB injuries are more likely to recur
        case
            when games_missed_pct >= 70 then 0.40 * positional_injury_multiplier
            when games_missed_pct >= 50 then 0.30 * positional_injury_multiplier
            when games_missed_pct >= 30 then 0.20 * positional_injury_multiplier
            when games_missed_pct >= 15 then 0.10 * positional_injury_multiplier
            else 0.00
        end as position_adjusted_availability_penalty

    from risk_factors
),

-- Apply composite risk penalty to VOR
final_risk_adjusted as (
    select
        *,

        -- Composite risk penalty (average of volatility + position-adjusted availability)
        -- Max penalty: ~35% (30% volatility + 40% availability with RB multiplier)
        round(
            (volatility_penalty + position_adjusted_availability_penalty) / 2,
            3
        ) as composite_risk_penalty,

        -- Risk-adjusted VOR = VOR × (1 - penalty)
        -- Players with high risk get VOR reduced
        round(
            value_over_replacement
            * (
                1
                - (volatility_penalty + position_adjusted_availability_penalty)
                / 2
            ),
            1
        ) as risk_adjusted_vor,

        -- Also apply to scarcity-adjusted VOR
        round(
            scarcity_adjusted_vor
            * (
                1
                - (volatility_penalty + position_adjusted_availability_penalty)
                / 2
            ),
            1
        ) as risk_adjusted_scarcity_vor,

        -- Risk tier for interpretation
        case
            when
                (volatility_penalty + position_adjusted_availability_penalty)
                / 2
                >= 0.25
                then 'HIGH_RISK'
            when
                (volatility_penalty + position_adjusted_availability_penalty)
                / 2
                >= 0.15
                then 'MODERATE_RISK'
            when
                (volatility_penalty + position_adjusted_availability_penalty)
                / 2
                >= 0.05
                then 'LOW_RISK'
            else 'VERY_LOW_RISK'
        end as risk_tier

    from risk_scores
)

select
    player_id,
    position,
    player_name,

    -- Original VOR values
    value_over_replacement as vor,
    scarcity_adjusted_vor as adj_vor,

    -- Risk components
    games_played,
    games_missed_pct,
    positional_injury_multiplier as pos_injury_risk,
    volatility_penalty as vol_penalty,

    -- Risk penalties
    availability_penalty as avail_penalty,
    position_adjusted_availability_penalty as pos_adj_avail_penalty,
    composite_risk_penalty,
    risk_adjusted_vor,

    -- Risk-adjusted VOR
    risk_adjusted_scarcity_vor,
    risk_tier,
    round(cv, 3) as coefficient_of_variation,

    -- For comparison: show VOR reduction
    round(value_over_replacement - risk_adjusted_vor, 1)
        as vor_reduction_from_risk,
    round(
        (value_over_replacement - risk_adjusted_vor)
        * 100.0
        / nullif(value_over_replacement, 0),
        1
    ) as vor_reduction_pct

from final_risk_adjusted
order by risk_adjusted_scarcity_vor desc
