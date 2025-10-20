{{ config(materialized='view') }}

/*
Calculate current player rankings based on season performance through current week.
Ranks players by total points (overall) and by position.
*/

with player_stats as (
    select * from {{ ref('stg_player_stats') }}
),

-- Get player position from draft picks
draft_picks as (
    select
        player_id,
        position,
        player_name
    from {{ ref('stg_draft_picks') }}
),

-- Aggregate season totals
season_totals as (
    select
        ps.player_id,
        dp.player_name,
        dp.position,
        -- Count only weeks where player actually played (not DNP/injured)
        sum(
            case
                when ps.pts_ppr is not null and ps.pts_ppr > 0 then 1 else 0
            end
        ) as games_played,
        sum(ps.pts_ppr) as total_points,
        -- PPG should only be for games actually played
        avg(
            case
                when ps.pts_ppr is not null and ps.pts_ppr > 0 then ps.pts_ppr
            end
        ) as points_per_game,
        sum(case when ps.gp > 0 then 1 else 0 end) as games_active

    from player_stats as ps
    left join draft_picks as dp
        on ps.player_id = dp.player_id
    -- Only rank drafted players with known positions
    where dp.position is not null
    group by ps.player_id, dp.player_name, dp.position
),

-- Rank overall and by position
ranked as (
    select
        *,
        row_number() over (order by total_points desc) as current_rank_overall,
        row_number()
            over (partition by position order by total_points desc)
            as current_rank_position,

        -- Calculate percentile rank
        percent_rank() over (order by total_points desc) as percentile_rank,

        -- Tier based on current performance
        case
            when
                row_number() over (order by total_points desc) <= 12
                then 'Elite (Top 12)'
            when
                row_number() over (order by total_points desc) <= 24
                then 'WR1/RB1 (13-24)'
            when
                row_number() over (order by total_points desc) <= 36
                then 'WR2/RB2 (25-36)'
            when
                row_number() over (order by total_points desc) <= 60
                then 'Flex Starter (37-60)'
            else 'Bench/Waiver (60+)'
        end as current_tier

    from season_totals
)

select * from ranked
order by current_rank_overall
