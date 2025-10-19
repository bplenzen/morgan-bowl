{{ config(materialized='view') }}

select
    cast(user_id as varchar) as user_id,
    display_name
from {{ source('staging', 'users') }}
