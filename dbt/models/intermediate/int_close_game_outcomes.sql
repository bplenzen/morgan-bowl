{{ config(materialized='ephemeral', tags=['luck', 'intermediate']) }}

-- Analyze close game outcomes (games decided by <5 points)
-- Close games are more influenced by luck/variance than blowouts

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

close_game_analysis as (
    select
        roster_id,
        manager_name,
        week,
        points,
        opponent_points,
        win_flag,
        abs(points - opponent_points) as point_differential,
        -- Define close game as <5 point differential
        case when abs(points - opponent_points) < 5 then 1 else 0 end
            as is_close_game,
        -- Close game outcomes
        case
            when abs(points - opponent_points) < 5 and win_flag = 1 then 1
            else 0
        end as close_win,
        case
            when abs(points - opponent_points) < 5 and win_flag = 0 then 1
            else 0
        end as close_loss
    from weekly_matchups
)

select
    roster_id,
    manager_name,
    week,
    points,
    opponent_points,
    win_flag,
    point_differential,
    is_close_game,
    close_win,
    close_loss,
    -- Calculate running totals
    sum(close_win) over (partition by roster_id) as total_close_wins,
    sum(close_loss) over (partition by roster_id) as total_close_losses,
    sum(is_close_game) over (partition by roster_id) as total_close_games,
    -- Close game win percentage (NULL if no close games)
    case
        when sum(is_close_game) over (partition by roster_id) > 0
            then
                sum(close_win) over (partition by roster_id)::double
                / sum(is_close_game) over (partition by roster_id)
    end as close_game_win_pct
from close_game_analysis
