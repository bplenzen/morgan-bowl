/*
Data Quality Test: Points Per Game Are Non-Negative
Ensures PPG values make sense (no negative points).
Negative PPG indicates data quality issues in player stats.
*/

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
