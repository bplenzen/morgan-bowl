{{ config(materialized='table') }}

with base as (
    select
        roster_id,
        owner_id,
        manager_name,
        sum(points) as points_for,
        sum(opponent_points) as points_against,
        sum(case when win_flag = 1 then 1 else 0 end) as wins,
        sum(case when win_flag = 0 then 1 else 0 end) as losses,
        count(*) as games_played
    from {{ ref('fct_matchups') }}
    group by 1, 2, 3
),

calculated as (
    select
        roster_id,
        owner_id,
        manager_name,
        points_for,
        points_against,
        wins,
        losses,
        games_played,
        wins + losses as decisions,
        case when games_played = 0 then 0 else wins::double / games_played end
            as win_pct,
        points_for - points_against as point_diff
    from base
)

select *
from calculated
