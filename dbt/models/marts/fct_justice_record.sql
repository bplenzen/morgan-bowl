{{ config(materialized='table') }}

-- ⚠️ DEPRECATED: This model is kept for backward compatibility but is no longer used in the dashboard
-- Replaced by fct_advanced_luck.sql (Oct 2025)
--
-- Reason for deprecation: Simple median-based approach (top 6 = win) is less sophisticated
-- than all-play record and expected wins methodology in fct_advanced_luck
--
-- This model still runs to avoid breaking CI/CD and existing tests
-- Consider removing in v2.0.0 after confirming no downstream dependencies

-- Get league configuration (playoff teams) from ingested data
-- Falls back to var if not available
with league_config as (
    select
        coalesce(playoff_teams, {{ var('playoff_teams', 6) }}) as playoff_teams
    from {{ ref('stg_league') }}
    limit 1
),

-- Rank teams by points each week (1 = highest scorer, 12 = lowest scorer)
weekly_ranks as (
    select
        m.week,
        m.roster_id,
        m.owner_id,
        m.manager_name,
        m.points,
        -- Rank teams by points (highest = 1)
        m.win_flag as actual_win,
        -- Also track actual win from matchup
        row_number()
            over (partition by m.week order by m.points desc)
            as points_rank
    from {{ ref('fct_matchups') }} as m
),

-- Determine if each team was in top half (justice win) or bottom half (justice loss)
-- Using playoff_teams from league configuration (auto-detected from Sleeper API)
weekly_justice_wins as (
    select
        wr.week,
        wr.roster_id,
        wr.owner_id,
        wr.manager_name,
        wr.points,
        wr.points_rank,
        -- Justice win if you're in the top playoff_teams scorers that week
        wr.actual_win,
        case
            when wr.points_rank <= lc.playoff_teams then 1
            else 0
        end as justice_win
    from weekly_ranks as wr
    cross join league_config as lc
),

-- Aggregate to season totals
season_totals as (
    select
        roster_id,
        owner_id,
        manager_name,
        count(*) as weeks_played,
        -- Justice record (wins against median)
        sum(justice_win) as justice_wins,
        count(*) - sum(justice_win) as justice_losses,
        -- Actual record
        sum(case when actual_win = 1 then 1 else 0 end) as actual_wins,
        sum(case when actual_win = 0 then 1 else 0 end) as actual_losses,
        -- Average points
        avg(points) as avg_points_per_week
    from weekly_justice_wins
    group by roster_id, owner_id, manager_name
)

select
    roster_id,
    owner_id,
    manager_name,
    weeks_played,

    -- Justice record
    justice_wins,
    justice_losses,
    actual_wins,

    -- Actual record
    actual_losses,
    round(justice_wins::double / weeks_played, 3) as justice_win_pct,
    round(actual_wins::double / weeks_played, 3) as actual_win_pct,

    -- The LUCK METRIC!
    actual_wins - justice_wins as luck_differential,

    -- Luck interpretation
    case
        when actual_wins - justice_wins > 1 then 'VERY LUCKY'
        when actual_wins - justice_wins = 1 then 'Lucky'
        when actual_wins - justice_wins = 0 then 'Fair'
        when actual_wins - justice_wins = -1 then 'Unlucky'
        when actual_wins - justice_wins < -1 then 'VERY UNLUCKY'
    end as luck_status,

    -- Supporting stats
    round(avg_points_per_week, 2) as avg_points_per_week

from season_totals
order by luck_differential desc, justice_wins desc
