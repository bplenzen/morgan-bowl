{{ config(materialized='view') }}

with source as (
    select * from {{ ref('preseason_rankings_2025') }}
),

renamed as (
    select
        player_id::varchar as player_id,
        player_name,
        position,
        team,
        preseason_rank_overall,
        preseason_rank_position,
        preseason_adp,
        tier as preseason_tier,

        -- Add position group for analysis
        case
            when position in ('RB') then 'RB'
            when position in ('WR') then 'WR'
            when position in ('QB') then 'QB'
            when position in ('TE') then 'TE'
            else 'OTHER'
        end as position_group

    from source
)

select * from renamed
