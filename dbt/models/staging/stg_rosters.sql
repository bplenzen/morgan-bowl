{{ config(materialized='view') }}

select
  roster_id,
  owner_id,
  players
from {{ source('staging', 'rosters') }}
