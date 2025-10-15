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
        on r.roster_id = m.roster_id
    left join {{ ref('stg_users') }} as u
        on u.user_id = r.owner_id
    left join {{ ref('stg_matchups') }} as opp
        on opp.week = m.week
        and opp.matchup_id = m.matchup_id
        and opp.roster_id <> m.roster_id
    left join {{ ref('stg_rosters') }} as opp_owner
        on opp_owner.roster_id = opp.roster_id
    left join {{ ref('stg_users') }} as opp_user
        on opp_user.user_id = opp_owner.owner_id
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
        else null
    end as win_flag
from base
