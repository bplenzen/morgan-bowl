{{ config(materialized='table') }}

with base as (
    select
        m.week,
        m.matchup_id,
        m.roster_id,
        m.points,
        r.owner_id,
        u.display_name as manager_name,
        opp.roster_id as opponent_roster_id,
        opp.points as opponent_points,
        opp_owner.owner_id as opponent_owner_id,
        opp_user.display_name as opponent_manager_name
    from {{ ref('stg_matchups') }} as m
    left join {{ ref('stg_rosters') }} as r
        on m.roster_id = r.roster_id
    left join {{ ref('stg_users') }} as u
        on r.owner_id = u.user_id
    left join {{ ref('stg_matchups') }} as opp
        on
            m.week = opp.week
            and m.matchup_id = opp.matchup_id
            and m.roster_id <> opp.roster_id
    left join {{ ref('stg_rosters') }} as opp_owner
        on opp.roster_id = opp_owner.roster_id
    left join {{ ref('stg_users') }} as opp_user
        on opp_owner.owner_id = opp_user.user_id
)

select
    week,
    matchup_id,
    roster_id,
    owner_id,
    manager_name,
    points,
    opponent_roster_id,
    opponent_owner_id,
    opponent_manager_name,
    opponent_points,
    points - opponent_points as point_diff,
    case
        when opponent_points is null then null
        when points > opponent_points then 1
        when points < opponent_points then 0
    end as win_flag
from base
