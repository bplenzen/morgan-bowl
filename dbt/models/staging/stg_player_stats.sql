{{ config(materialized='view') }}

/*
Unified player stats across all weeks.
Dynamically detects available player_stats_week_XX tables and unions them.
This makes the model scalable - automatically includes new weeks as they're ingested.
*/

{#- Dynamically discover available weeks by querying information_schema -#}
{%- set week_query -%}
    select distinct
        cast(replace(table_name, 'player_stats_week_', '') as integer) as week_num
    from information_schema.tables
    where table_schema = 'staging'
      and table_name like 'player_stats_week_%'
    order by week_num
{%- endset -%}

{%- set results = run_query(week_query) -%}

{%- if execute -%}
  {%- set available_weeks = results.columns[0].values() -%}
  {{ log("Auto-detected " ~ available_weeks|length ~ " weeks of player stats: " ~ available_weeks|join(', '), info=True) }}
{%- else -%}
  {%- set available_weeks = [] -%}
{%- endif -%}

with all_weeks as (
    {% for week in available_weeks %}
    select
        player_id,
        week,
        season,
        pts_ppr,
        pts_half_ppr,
        pts_std,
        gp,
        gms_active,
        pos_rank_ppr,
        pos_rank_half_ppr,
        pos_rank_std
    from staging.player_stats_week_{{ '%02d'|format(week) }}
    where player_id not like 'TEAM_%'  -- Exclude team defenses
    {% if not loop.last %}
    union all
    {% endif %}
    {% endfor %}
)

select * from all_weeks
