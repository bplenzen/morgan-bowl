/*
Data Quality Test: Position Rankings Are Unique
Ensures each player appears only once per position ranking.
Duplicate rankings indicate calculation errors in int_current_player_rankings.
*/

with duplicate_position_ranks as (
    select
        position,
        current_rank_position,
        count(*) as player_count,
        string_agg(player_name, ', ') as players
    from {{ ref('int_current_player_rankings') }}
    where current_rank_position is not null
    group by position, current_rank_position
    having count(*) > 1
)

select * from duplicate_position_ranks
