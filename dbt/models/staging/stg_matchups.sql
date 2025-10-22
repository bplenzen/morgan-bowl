{{ config(materialized='view') }}

with unioned as (
    select
        1 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_01') }}

    union all

    select
        2 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_02') }}

    union all

    select
        3 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_03') }}

    union all

    select
        4 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_04') }}

    union all

    select
        5 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_05') }}

    union all

    select
        6 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_06') }}

    union all

    select
        7 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_07') }}
)

select
    week,
    matchup_id,
    roster_id,
    points
from unioned
