{{ config(materialized='table') }}

-- Advanced luck metrics using multiple statistical approaches
-- This goes beyond simple median-based "justice record"

with weekly_matchups as (
    select
        week,
        roster_id,
        manager_name,
        points,
        opponent_points,
        win_flag
    from {{ ref('fct_matchups') }}
),

-- 1. ALL-PLAY RECORD: If you played everyone each week, how many would you beat?
all_play_results as (
    select
        m1.week,
        m1.roster_id,
        m1.manager_name,
        m1.points,
        -- Count how many teams you would have beaten this week
        sum(case when m1.points > m2.points then 1 else 0 end) as all_play_wins,
        -- Total opponents (should be 11 with 12 teams)
        count(*) as all_play_games
    from weekly_matchups as m1
    cross join weekly_matchups as m2
    where
        m1.week = m2.week
        and m1.roster_id <> m2.roster_id
    group by m1.week, m1.roster_id, m1.manager_name, m1.points
),

all_play_season as (
    select
        roster_id,
        manager_name,
        sum(all_play_wins) as all_play_wins,
        sum(all_play_games) as all_play_games,
        round(sum(all_play_wins)::double / sum(all_play_games), 3)
            as all_play_win_pct
    from all_play_results
    group by roster_id, manager_name
),

-- 2. EXPECTED WINS based on all-play win percentage
expected_wins_calc as (
    select
        roster_id,
        manager_name,
        all_play_wins,
        all_play_games,
        all_play_win_pct,
        -- Expected wins = all-play win% × actual games played
        round(
            all_play_win_pct * (select count(distinct week) from weekly_matchups
            ),
            2
        ) as expected_wins
    from all_play_season
),

-- 3. SCHEDULE STRENGTH LUCK: Did you face opponents on their hot/cold weeks?
opponent_performance as (
    select
        m.week,
        m.roster_id,
        m.manager_name,
        m.opponent_points,
        -- Get opponent's season average
        avg(opp_all.points)
            over (partition by m.week, m.opponent_roster_id)
            as opponent_avg_points
    from {{ ref('fct_matchups') }} as m
    left join weekly_matchups as opp_all
        on m.opponent_roster_id = opp_all.roster_id
),

schedule_luck as (
    select
        roster_id,
        manager_name,
        -- Positive = faced opponents on good weeks (unlucky)
        -- Negative = faced opponents on bad weeks (lucky)
        round(avg(opponent_points - opponent_avg_points), 2)
            as schedule_luck_index
    from opponent_performance
    group by roster_id, manager_name
),

-- 4. CLOSE GAME ANALYSIS: Games decided by <10 points (somewhat arbitrary)
close_games as (
    select
        roster_id,
        manager_name,
        sum(case
            when abs(points - opponent_points) < 10 and win_flag = 1 then 1
            else 0
        end) as close_wins,
        sum(case
            when abs(points - opponent_points) < 10 and win_flag = 0 then 1
            else 0
        end) as close_losses,
        sum(case when abs(points - opponent_points) < 10 then 1 else 0 end)
            as total_close_games
    from weekly_matchups
    group by roster_id, manager_name
),

-- 5. CONSISTENCY METRICS
consistency as (
    select
        roster_id,
        manager_name,
        round(stddev(points), 2) as points_stddev,
        round(avg(points), 2) as avg_points,
        round(min(points), 2) as min_points,
        round(max(points), 2) as max_points
    from weekly_matchups
    group by roster_id, manager_name
),

-- Get actual record
actual_record as (
    select
        roster_id,
        manager_name,
        wins as actual_wins,
        losses as actual_losses
    from {{ ref('fct_standings') }}
),

-- Combine everything
final as (
    select
        ar.roster_id,
        ar.manager_name,

        -- Actual record
        ar.actual_wins,
        ar.actual_losses,

        -- Expected wins (most sophisticated metric)
        ew.expected_wins,
        ew.all_play_wins,

        -- All-play stats
        ew.all_play_games,
        ew.all_play_win_pct,
        sl.schedule_luck_index,

        -- Schedule luck
        cg.close_wins,

        -- Close games
        cg.close_losses,
        cg.total_close_games,
        c.points_stddev,
        c.avg_points,

        -- Consistency
        round(ar.actual_wins - ew.expected_wins, 2) as wins_over_expected,
        case
            when cg.total_close_games > 0
                then round(cg.close_wins::double / cg.total_close_games, 3)
        end as close_game_win_pct,
        c.max_points - c.min_points as points_range,

        -- COMPOSITE LUCK SCORE (normalized 0-100, 50 = average luck)
        -- Factors: wins over expected (60%), schedule luck (20%), close game % (20%)
        round(
            50
            -- ±10 per win over/under expected
            + (ar.actual_wins - ew.expected_wins) * 10
            + (sl.schedule_luck_index * -0.5)  -- Schedule harder = unlucky
            + case
                when cg.total_close_games > 0
                    then
                        ((cg.close_wins::double / cg.total_close_games) - 0.5)
                        * 20
                else 0
            end,
            1
        ) as composite_luck_score

    from actual_record as ar
    left join
        expected_wins_calc as ew
        on ar.roster_id = ew.roster_id and ar.manager_name = ew.manager_name
    left join
        schedule_luck as sl
        on ar.roster_id = sl.roster_id and ar.manager_name = sl.manager_name
    left join
        close_games as cg
        on ar.roster_id = cg.roster_id and ar.manager_name = cg.manager_name
    left join
        consistency as c
        on ar.roster_id = c.roster_id and ar.manager_name = c.manager_name
)

select
    roster_id,
    manager_name,

    -- Actual vs Expected
    actual_wins,
    actual_losses,
    expected_wins,
    wins_over_expected,

    -- All-play record (beat X out of 66 possible matchups if 6 weeks × 11 opponents)
    all_play_wins,
    all_play_games,
    all_play_win_pct,

    -- Schedule difficulty
    schedule_luck_index,
    close_wins,

    -- Close game performance
    close_losses,
    total_close_games,
    close_game_win_pct,
    points_stddev,

    -- Consistency metrics
    avg_points,
    points_range,
    composite_luck_score,

    -- OVERALL LUCK RATING (0-100 scale, 50 = average)
    case
        when schedule_luck_index > 5 then 'Brutal Schedule'
        when schedule_luck_index > 2 then 'Tough Schedule'
        when schedule_luck_index > -2 then 'Average Schedule'
        when schedule_luck_index > -5 then 'Easy Schedule'
        else 'Cupcake Schedule'
    end as schedule_difficulty,
    case
        when composite_luck_score >= 65 then 'VERY LUCKY'
        when composite_luck_score >= 55 then 'Lucky'
        when composite_luck_score >= 45 then 'Fair'
        when composite_luck_score >= 35 then 'Unlucky'
        else 'VERY UNLUCKY'
    end as luck_rating

from final
order by composite_luck_score desc
