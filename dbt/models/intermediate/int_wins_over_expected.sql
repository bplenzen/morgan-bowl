{{ config(materialized='ephemeral', tags=['luck', 'intermediate']) }}

-- Calculate all-play expected wins and wins over expected
-- This uses the all-play methodology: if you played everyone each week, how many would you beat?

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

-- All-play record: count wins against all teams each week
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

-- Aggregate to season level
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

-- Calculate expected wins based on total weeks played
total_weeks as (
    select count(distinct week) as total_weeks
    from weekly_matchups
),

expected_wins_calc as (
    select
        aps.roster_id,
        aps.manager_name,
        aps.all_play_wins,
        aps.all_play_games,
        aps.all_play_win_pct,
        -- Expected wins = all-play win% × actual games played
        round(aps.all_play_win_pct * tw.total_weeks, 2) as expected_wins
    from all_play_season as aps
    cross join total_weeks as tw
),

-- Get actual wins
actual_record as (
    select
        fs.roster_id,
        fs.manager_name,
        fs.wins as actual_wins,
        fs.losses as actual_losses
    from {{ ref('fct_standings') }} as fs
)

select
    ar.roster_id,
    ar.manager_name,
    ar.actual_wins,
    ar.actual_losses,
    ew.expected_wins,
    ew.all_play_wins,
    ew.all_play_games,
    ew.all_play_win_pct,
    -- Wins over expected (core luck metric)
    round(ar.actual_wins - ew.expected_wins, 2) as wins_over_expected
from actual_record as ar
left join expected_wins_calc as ew
    on ar.roster_id = ew.roster_id and ar.manager_name = ew.manager_name
