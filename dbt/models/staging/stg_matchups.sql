{{ config(materialized='view') }}

with unioned as (
    {% set weeks = range(1, 7) %}  -- Weeks 1-6
    {% for week in weeks %}
        select
            {{ week }} as week,
            matchup_id,
            roster_id,
            points
        from {{ source('staging', 'matchups_week_' ~ '%02d' | format(week)) }}
        {% if not loop.last %}
            union all
        {% endif %}
    {% endfor %}
)

select
    week,
    matchup_id,
    roster_id,
    points
from unioned
