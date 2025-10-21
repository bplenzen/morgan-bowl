/*
Data Quality Test: Points Per Game Are Non-Negative
Flags players with negative fantasy points.
Note: Negative points are valid in fantasy football (fumbles, INTs, etc.)
This is a WARNING to identify underperforming players, not a data quality issue.
*/
{{ config(severity='warn') }}

with negative_ppg as (
    select
        player_id,
        player_name,
        position,
        points_per_game,
        total_points,
        games_played
    from {{ ref('int_current_player_rankings') }}
    where points_per_game < 0
       or total_points < 0
)

select * from negative_ppg
