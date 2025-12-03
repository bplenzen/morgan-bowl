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

    union all

    select
        8 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_08') }}

    union all

    select
        9 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_09') }}

    union all

    select
        10 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_10') }}

    union all

    select
        11 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_11') }}

    union all

    select
        12 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_12') }}

    union all

    select
        13 as week,
        matchup_id,
        roster_id,
        points
    from {{ source('staging', 'matchups_week_13') }}
)

select
    week,
    matchup_id,
    roster_id,
    points
from unioned
