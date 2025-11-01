{{ config(materialized='table') }}

/*
Historical Average PPG by Position and Rank

Calculates average points per game by position and positional rank using
actual season performance data. This provides more realistic PPG estimates
than hardcoded tiers for the pick-value curve.

IMPORTANT CAVEAT: This model uses current season performance data, which
creates look-ahead bias when estimating preseason expected value. This is
an interim solution until FantasyPros API integration (see task #16).

The long-term fix is to use actual preseason expert projections, which
represent true draft-day expectations without hindsight.

For now, this gives better estimates than completely made-up tiers.
*/

with current_rankings as (
    select * from {{ ref('int_current_player_rankings') }}
),

-- Calculate positional averages by rank
positional_averages as (
    select
        position,
        current_rank_position,
        round(avg(points_per_game), 1) as avg_ppg,
        round(stddev(points_per_game), 1) as stddev_ppg,
        count(*) as sample_size
    from current_rankings
    where
        games_played >= 8  -- Full season data only for stable estimates
        and points_per_game > 0  -- Exclude players with no production
        -- Exclude K/DEF (streaming positions)
        and position in ('QB', 'RB', 'WR', 'TE')
    group by position, current_rank_position
)

select
    position,
    current_rank_position as rank_position,
    avg_ppg as historical_avg_ppg,
    stddev_ppg as historical_stddev_ppg,
    sample_size,

    -- Smoothed estimate using nearby ranks (handles small sample sizes)
    -- Window: ±2 ranks for stability without over-smoothing
    round(
        avg(avg_ppg) over (
            partition by position
            order by current_rank_position
            rows between 2 preceding and 2 following
        ),
        1
    ) as smoothed_ppg

from positional_averages
order by position, rank_position
