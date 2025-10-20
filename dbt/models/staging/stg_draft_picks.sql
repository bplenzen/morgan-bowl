{{ config(materialized='view') }}

with source as (
    select * from {{ source('staging', 'draft_picks') }}
),

renamed as (
    select
        draft_id,
        player_id,
        roster_id,
        round,
        draft_slot,
        pick_no,

        -- Extract player info from metadata
        metadata['first_name']::varchar as first_name,
        metadata['last_name']::varchar as last_name,
        metadata['position']::varchar as position,
        metadata['team']::varchar as team,
        metadata['status']::varchar as status,
        metadata['years_exp']::varchar as years_exp,

        -- Calculated fields
        concat(
            metadata['first_name']::varchar,
            ' ',
            metadata['last_name']::varchar
        ) as player_name,

        -- Draft tier based on round
        case
            when round = 1 then 'Elite (Round 1)'
            when round = 2 then 'High Value (Round 2)'
            when round = 3 then 'Solid (Round 3)'
            when round <= 5 then 'Mid Round (4-5)'
            when round <= 8 then 'Late Round (6-8)'
            else 'Deep Sleeper (9+)'
        end as draft_tier

    from source
)

select * from renamed
