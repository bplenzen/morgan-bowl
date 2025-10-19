{{ config(materialized='view') }}

select
    league_id,
    name
from {{ source('staging', 'league') }}
