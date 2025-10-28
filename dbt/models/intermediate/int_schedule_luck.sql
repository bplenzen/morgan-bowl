{{ config(materialized='ephemeral', tags=['luck', 'intermediate']) }}

-- Calculate schedule luck based on opponent strength timing
-- Positive values = faced opponents on their good weeks (unlucky)
-- Negative values = faced opponents on their bad weeks (lucky)

with weekly_matchups as (
    select
        fm.week,
        fm.roster_id,
        fm.manager_name,
        fm.points,
        fm.opponent_points,
        fm.opponent_roster_id
    from {{ ref('fct_matchups') }} as fm
),

-- Get each opponent's season average points
opponent_season_avg as (
    select
        roster_id,
        avg(points) as avg_points
    from weekly_matchups
    group by roster_id
),

-- Calculate per-week opponent performance vs their average
opponent_performance as (
    select
        wm.week,
        wm.roster_id,
        wm.manager_name,
        wm.opponent_points,
        wm.opponent_roster_id,
        osa.avg_points as opponent_avg_points,
        -- How much better/worse was opponent than their average this week
        wm.opponent_points - osa.avg_points as opponent_deviation
    from weekly_matchups as wm
    left join opponent_season_avg as osa
        on wm.opponent_roster_id = osa.roster_id
)

select
    roster_id,
    manager_name,
    week,
    opponent_roster_id,
    opponent_points,
    opponent_avg_points,
    opponent_deviation,
    -- Schedule luck index: avg deviation of opponents faced
    avg(opponent_deviation) over (
        partition by roster_id
    ) as schedule_luck_index
from opponent_performance
