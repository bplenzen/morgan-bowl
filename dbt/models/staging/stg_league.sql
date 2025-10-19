{{ config(materialized='view') }}

select
    league_id,
    name,
    season,
    total_rosters,
    playoff_teams,
    playoff_week_start,
    status
from {{ source('staging', 'league') }}
