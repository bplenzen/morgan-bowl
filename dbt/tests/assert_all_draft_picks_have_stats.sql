/*
Data Quality Test: All Draft Picks Have Stats
Ensures every drafted player (except DEF/K) has player stats.
Missing stats are common for bench players, injured players, or those who haven't played.
This is a WARNING - it won't block the pipeline.
*/
{{ config(severity='warn') }}

with draft_picks_without_stats as (
    select
        d.player_id,
        d.player_name,
        d.position,
        d.pick_no,
        d.round
    from {{ ref('stg_draft_picks') }} d
    left join {{ ref('stg_player_stats') }} s
        on d.player_id = s.player_id
    where s.player_id is null
      -- Exclude positions that don't have individual stats
      and d.position not in ('DEF', 'K')
      -- Exclude null positions (data quality issue in draft data)
      and d.position is not null
)

select * from draft_picks_without_stats
