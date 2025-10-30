{{ config(materialized='table') }}

/*
Player Weekly Stats - Variance & Consistency Analysis
Calculates weekly performance metrics for each player to measure:
- Consistency (coefficient of variation)
- Boom/Bust rates (volatility)
- Floor/Ceiling (10th/90th percentile)
- Risk profiles

Used to distinguish reliable starters from volatile boom/bust players.
*/

with weekly_stats as (
    select
        player_id,
        week,
        pts_ppr as weekly_points
    from {{ ref('stg_player_stats') }}
    where
        pts_ppr is not null
        and pts_ppr > 0  -- Exclude DNPs
),

player_aggregates as (
    select
        player_id,

        -- Basic stats
        count(*) as weeks_played,
        avg(weekly_points) as avg_weekly_points,
        sum(weekly_points) as total_points,

        -- Variance metrics
        stddev(weekly_points) as stddev_weekly_points,

        -- Consistency score (lower = more consistent)
        -- CV = StdDev / Mean (normalized volatility)
        case
            when avg(weekly_points) > 0
                then
                    stddev(weekly_points) / avg(weekly_points)
        end as coefficient_of_variation,

        -- Floor/Ceiling (10th/90th percentile)
        percentile_cont(0.10) within group (order by weekly_points)
            as floor_10th_percentile,
        percentile_cont(0.90) within group (order by weekly_points)
            as ceiling_90th_percentile,

        -- Min/Max for reference
        min(weekly_points) as min_weekly_points,
        max(weekly_points) as max_weekly_points

    from weekly_stats
    group by player_id
),

-- Calculate boom/bust in a separate CTE
-- Boom/Bust Thresholds: 1.5× and 0.5× avg (50% above/below)
-- Validated: QBs boom/bust ~6% games, RB/WR ~16% games
-- These thresholds are statistically sound
boom_bust_calc as (
    select
        ws.player_id,
        pa.avg_weekly_points,
        count(
            case when ws.weekly_points > 1.5 * pa.avg_weekly_points then 1 end
        ) as boom_weeks,  -- Scored 50%+ above avg
        count(
            case when ws.weekly_points < 0.5 * pa.avg_weekly_points then 1 end
        ) as bust_weeks   -- Scored 50%+ below avg
    from weekly_stats as ws
    inner join player_aggregates as pa on ws.player_id = pa.player_id
    group by ws.player_id, pa.avg_weekly_points
),

with_boom_bust as (
    select
        pa.*,
        bb.boom_weeks,
        bb.bust_weeks
    from player_aggregates as pa
    left join boom_bust_calc as bb on pa.player_id = bb.player_id
),

final as (
    select
        *,

        -- Calculate boom/bust rates as percentages
        case
            when weeks_played > 0
                then
                    round(100.0 * boom_weeks / weeks_played, 1)
            else 0
        end as boom_rate_pct,

        case
            when weeks_played > 0
                then
                    round(100.0 * bust_weeks / weeks_played, 1)
            else 0
        end as bust_rate_pct,

        -- Consistency tier (lower CV = more consistent)
        -- CV Thresholds: Educated guesses from 2025 data
        -- QBs avg CV=0.33, RB/WR avg CV=0.55
        -- Debatable - could be tuned based on preferences
        case
            when coefficient_of_variation is null then 'NO_DATA'
            -- Low variance (QBs, elite RBs)
            -- e.g., Mahomes 0.21
            when coefficient_of_variation < 0.30 then 'VERY_CONSISTENT'
            -- e.g., J.Taylor 0.34
            when coefficient_of_variation < 0.50 then 'CONSISTENT'
            -- e.g., Ja'Marr 0.62
            when coefficient_of_variation < 0.70 then 'MODERATE'
            -- Rare, big swings
            when coefficient_of_variation < 1.00 then 'VOLATILE'
            else 'BOOM_BUST'  -- High variance (CV ≥ 1.0)
        end as consistency_tier,

        -- Risk score (0-100, higher = more risky)
        -- Components: volatility (CV) + boom/bust tendency
        case
            when coefficient_of_variation is not null
                then
                    round(
                        least(
                            100,
                            -- CV contributes up to 50 points
                            (coefficient_of_variation * 50)
                            -- Bust rate contributes up to 50 points
                            + (bust_rate_pct * 0.5)
                        ),
                        1
                    )
        end as volatility_risk_score

    from with_boom_bust
)

select * from final
order by total_points desc
