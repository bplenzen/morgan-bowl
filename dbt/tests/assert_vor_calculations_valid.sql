/*
Data Quality Test: VOR Calculations Are Valid
Ensures Value Over Replacement values are within reasonable bounds.
VOR can be negative for bad picks, but should not be extremely negative (< -100)
or unrealistically high (> 250). NULL VOR despite games played indicates missing data.
Note: Increased threshold to 250 to account for truly elite performances (e.g., CMC in 2024).
*/

with invalid_vor as (
    select
        player_id,
        player_name,
        position,
        current_rank_position,
        points_per_game,
        value_over_replacement,
        replacement_ppg,
        games_played,
        -- Flag the issue
        case
            when value_over_replacement < -100 then 'VOR too negative (< -100)'
            when value_over_replacement > 250 then 'VOR too high (> 250)'
            when value_over_replacement is null and games_played > 0 and points_per_game is not null then 'VOR is NULL despite valid data'
        end as issue
    from {{ ref('fct_draft_performance') }}
    where (value_over_replacement < -100
           or value_over_replacement > 250
           or (value_over_replacement is null and games_played > 0 and points_per_game is not null))
      -- Exclude positions that don't have VOR calculated
      and position not in ('DEF', 'K')
)

select * from invalid_vor
