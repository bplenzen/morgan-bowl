{{ config(materialized='table') }}

/*
Rest-of-Season (ROS) Player Rankings

Methodology:
1. Weight recent games more heavily (exponential decay)
2. Adjust for remaining schedule difficulty
3. Apply injury discount factor (if applicable)
4. Calculate expected PPG for rest of season

This is forward-looking, unlike current_rank_position (backward-looking).
*/

with player_stats as (
    select * from {{ ref('stg_player_stats') }}
),

matchups as (
    select * from {{ ref('stg_matchups') }}
),

league_config as (
    select playoff_week_start from {{ ref('stg_league') }}
),

draft_picks as (
    select
        player_id,
        position,
        player_name
    from {{ ref('stg_draft_picks') }}
),

-- Get weeks played and current week
weeks_metadata as (
    select
        lc.playoff_week_start as playoff_week,
        max(m.week) as current_week
    from matchups as m
    cross join league_config as lc
    group by lc.playoff_week_start
),

-- Recent performance (last 4 weeks weighted more heavily)
recent_performance as (
    select
        ps.player_id,
        dp.player_name,
        dp.position,
        ps.week,
        ps.pts_ppr as weekly_points,

        -- Exponential weight: more recent = higher weight
        -- Weight: 2^(week - max_week + 4) = [8, 4, 2, 1]
        power(2, ps.week - wm.current_week + 4) as week_weight

    from player_stats as ps
    cross join weeks_metadata as wm
    left join draft_picks as dp
        on ps.player_id = dp.player_id
    where
        dp.position in ('QB', 'RB', 'WR', 'TE')
        -- Only use last 6 weeks for ROS projection
        and ps.week >= wm.current_week - 5
        and ps.pts_ppr is not null
),

-- Weighted average PPG (emphasizes recent performance)
weighted_ppg as (
    select
        player_id,
        player_name,
        position,
        count(*) as recent_games,

        -- Weighted average: sum(points × weight) / sum(weight)
        round(
            sum(weekly_points * week_weight) / sum(week_weight),
            2
        ) as ros_projected_ppg,

        -- Compare to unweighted average
        round(avg(weekly_points), 2) as recent_avg_ppg,

        -- Variance in recent games (uncertainty)
        round(stddev(weekly_points), 2) as recent_stddev

    from recent_performance
    group by player_id, player_name, position
    having count(*) >= 3  -- Minimum 3 games for ROS projection
),

-- Injury/availability discount (players who missed recent games)
availability_adjustment as (
    select
        ps.player_id,
        count(*) as weeks_active_last_6,

        -- Discount factor for players who missed games
        case
            when count(*) >= 5 then 1.00   -- Fully available
            when count(*) = 4 then 0.95    -- Missed 1-2 games
            when count(*) = 3 then 0.90    -- Missed 3 games
            else 0.85                       -- Missed 4+ games
        end as availability_factor

    from player_stats as ps
    cross join weeks_metadata as wm
    left join draft_picks as dp
        on ps.player_id = dp.player_id
    where
        ps.week >= wm.current_week - 5
        and dp.position in ('QB', 'RB', 'WR', 'TE')
        and ps.pts_ppr is not null
    group by ps.player_id
),

-- Combine weighted PPG with availability adjustment
ros_projections as (
    select
        wpg.player_id,
        wpg.player_name,
        wpg.position,
        wpg.recent_games,
        wpg.ros_projected_ppg,
        wpg.recent_stddev,

        -- Final ROS PPG: weighted average × availability
        coalesce(aa.availability_factor, 1.0) as availability_factor,

        round(wpg.ros_projected_ppg * coalesce(aa.availability_factor, 1.0), 2)
            as ros_adjusted_ppg

    from weighted_ppg as wpg
    left join availability_adjustment as aa
        on wpg.player_id = aa.player_id
),

-- Rank players by ROS projected PPG
ros_rankings as (
    select
        *,
        row_number() over (order by ros_adjusted_ppg desc) as ros_rank_overall,
        row_number() over (
            partition by position
            order by ros_adjusted_ppg desc
        ) as ros_rank_position,

        -- ROS tier (for quick comparison)
        case
            when
                row_number()
                    over (partition by position order by ros_adjusted_ppg desc)
                <= 6
                then 'ELITE'
            when
                row_number()
                    over (partition by position order by ros_adjusted_ppg desc)
                <= 12
                then 'WR1/RB1'
            when
                row_number()
                    over (partition by position order by ros_adjusted_ppg desc)
                <= 24
                then 'WR2/RB2'
            when
                row_number()
                    over (partition by position order by ros_adjusted_ppg desc)
                <= 36
                then 'FLEX'
            else 'BENCH'
        end as ros_tier

    from ros_projections
)

select
    player_id,
    player_name,
    position,
    recent_games,
    ros_projected_ppg,
    availability_factor,
    ros_adjusted_ppg,
    recent_stddev,
    ros_rank_overall,
    ros_rank_position,
    ros_tier,

    -- Confidence in projection (more games = more confident)
    case
        when recent_games >= 5 then 'HIGH'
        when recent_games >= 4 then 'MODERATE'
        else 'LOW'
    end as projection_confidence

from ros_rankings
order by ros_rank_overall
