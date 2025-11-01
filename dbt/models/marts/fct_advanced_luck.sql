{{ config(materialized='table') }}

-- Advanced luck metrics using multiple statistical approaches
-- This goes beyond simple median-based "justice record"
-- Refactored to use composable intermediate models (MP-1)

with weekly_matchups as (
    select
        fm.week,
        fm.roster_id,
        fm.manager_name,
        fm.points,
        fm.opponent_points,
        fm.win_flag
    from {{ ref('fct_matchups') }} as fm
),

-- WINS OVER EXPECTED: Use pre-calculated all-play based expected wins
wins_over_expected as (
    select
        roster_id,
        manager_name,
        actual_wins,
        actual_losses,
        expected_wins,
        all_play_wins,
        all_play_games,
        all_play_win_pct,
        wins_over_expected
    from {{ ref('int_wins_over_expected') }}
),

-- SCHEDULE LUCK: Use pre-calculated opponent strength timing
schedule_luck as (
    select
        roster_id,
        manager_name,
        round(avg(schedule_luck_index), 2) as schedule_luck_index
    from {{ ref('int_schedule_luck') }}
    group by roster_id, manager_name
),

-- CLOSE GAMES: Use pre-calculated close game outcomes
close_games as (
    select
        roster_id,
        manager_name,
        max(total_close_wins) as close_wins,
        max(total_close_losses) as close_losses,
        max(total_close_games) as total_close_games,
        max(close_game_win_pct) as close_game_win_pct
    from {{ ref('int_close_game_outcomes') }}
    group by roster_id, manager_name
),

-- CONSISTENCY METRICS
consistency as (
    select
        wm.roster_id,
        wm.manager_name,
        round(stddev(wm.points), 2) as points_stddev,
        round(avg(wm.points), 2) as avg_points,
        round(min(wm.points), 2) as min_points,
        round(max(wm.points), 2) as max_points
    from weekly_matchups as wm
    group by wm.roster_id, wm.manager_name
),

-- Combine everything
final as (
    select
        woe.roster_id,
        woe.manager_name,

        -- Actual record
        woe.actual_wins,
        woe.actual_losses,

        -- Expected wins (point estimate from deterministic all-play)
        woe.expected_wins,

        -- Expected wins uncertainty (from Monte Carlo / Wilson score interval)
        mc.expected_wins_p05,
        mc.expected_wins_p50,
        mc.expected_wins_p95,
        mc.expected_wins_ci_width,
        mc.expected_wins_std_error,

        woe.all_play_wins,

        -- All-play stats
        woe.all_play_games,
        woe.all_play_win_pct,
        sl.schedule_luck_index,

        -- Schedule luck
        cg.close_wins,

        -- Close games
        cg.close_losses,
        cg.total_close_games,
        c.points_stddev,
        c.avg_points,

        -- Consistency
        woe.wins_over_expected,

        -- Wins over expected with uncertainty bounds
        round(woe.actual_wins - mc.expected_wins_p50, 2)
            as wins_over_expected_p50,
        round(woe.actual_wins - mc.expected_wins_p95, 2)
            as wins_over_expected_lower,
        round(woe.actual_wins - mc.expected_wins_p05, 2)
            as wins_over_expected_upper,

        case
            when cg.total_close_games > 0
                then round(cg.close_wins::double / cg.total_close_games, 3)
        end as close_game_win_pct,
        c.max_points - c.min_points as points_range,

        -- COMPOSITE LUCK SCORE (normalized 0-100, 50 = average luck)
        -- MULTI-COMPONENT FORMULA (Nov 2025): Reintroduced schedule/close components
        -- based on user feedback that these factors should be explicitly weighted.
        -- Weights: 60% wins over expected, 35% schedule luck, 5% close games
        -- Formula components:
        --   1. Wins over expected × 10 (core all-play luck metric)
        --   2. Schedule luck index × -1.0 (negative because positive = unlucky)
        --   3. (Close game win% - 0.5) × 5 (centered at 50% baseline)
        round(
            50
            + (woe.wins_over_expected * 10)  -- 60% weight: ±30 pts for ±3 wins
            -- 35% weight: ±20 pts
            + (coalesce(sl.schedule_luck_index, 0) * -1.0)
            + (coalesce(
                case
                    when cg.total_close_games > 0
                        then
                            (cg.close_wins::double / cg.total_close_games) - 0.5
                    else 0
                end, 0
            ) * 5),  -- 5% weight: ±2.5 pts
            1
        ) as composite_luck_score

    from wins_over_expected as woe
    left join
        {{ ref('int_expected_wins_uncertainty') }} as mc
        on woe.roster_id = mc.roster_id and woe.manager_name = mc.manager_name
    left join
        schedule_luck as sl
        on woe.roster_id = sl.roster_id and woe.manager_name = sl.manager_name
    left join
        close_games as cg
        on woe.roster_id = cg.roster_id and woe.manager_name = cg.manager_name
    left join
        consistency as c
        on woe.roster_id = c.roster_id and woe.manager_name = c.manager_name
)

select
    f.roster_id,
    f.manager_name,

    -- Actual vs Expected
    f.actual_wins,
    f.actual_losses,
    f.expected_wins,
    f.wins_over_expected,

    -- Expected wins uncertainty (Monte Carlo / Wilson score intervals)
    f.expected_wins_p05,
    f.expected_wins_p50,
    f.expected_wins_p95,
    f.expected_wins_ci_width,
    f.expected_wins_std_error,

    -- Wins over expected with uncertainty bounds
    f.wins_over_expected_p50,
    f.wins_over_expected_lower,
    f.wins_over_expected_upper,

    -- All-play record (beat X out of 66 possible matchups if 6 weeks × 11 opponents)
    f.all_play_wins,
    f.all_play_games,
    f.all_play_win_pct,

    -- Schedule difficulty
    f.schedule_luck_index,
    f.close_wins,

    -- Close game performance
    f.close_losses,
    f.total_close_games,
    f.close_game_win_pct,
    f.points_stddev,

    -- Consistency metrics
    f.avg_points,
    f.points_range,
    f.composite_luck_score,

    -- OVERALL LUCK RATING (0-100 scale, 50 = average)
    case
        when f.schedule_luck_index > 5 then 'Brutal Schedule'
        when f.schedule_luck_index > 2 then 'Tough Schedule'
        when f.schedule_luck_index > -2 then 'Average Schedule'
        when f.schedule_luck_index > -5 then 'Easy Schedule'
        else 'Cupcake Schedule'
    end as schedule_difficulty,
    case
        when f.composite_luck_score >= 65 then 'VERY LUCKY'
        when f.composite_luck_score >= 55 then 'Lucky'
        when f.composite_luck_score >= 45 then 'Fair'
        when f.composite_luck_score >= 35 then 'Unlucky'
        else 'VERY UNLUCKY'
    end as luck_rating

from final as f
order by f.composite_luck_score desc
