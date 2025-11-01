{{ config(materialized='table') }}

/*
Expected Value by Pick - Pick-Value Curve

Calculates expected VOR for each draft pick using LOESS-style smoothing
over historical preseason ADP data. This enables:

1. Cross-positional opportunity cost (is QB5 at pick 40 a reach vs RB15?)
2. Identification of true "steals" vs "reaches"
3. Fair comparison across positions with different scarcity curves

Methodology:
- Uses preseason ADP as proxy for draft-day expected value
- Smooths expected VOR using moving average (LOESS approximation in SQL)
- Window size: ±10 picks for stability without over-smoothing
- Frozen at draft time - never changes with actual performance

This creates a position-agnostic "value curve" that shows what
VOR was reasonably expected at each pick based on consensus rankings.

Example: If pick 40 has expected VOR of 50 (based on historic ADP),
then drafting a player projected for 30 VOR is a -20 reach,
while getting someone projected for 70 VOR is a +20 value pick.
*/

with league_config as (
    select total_rosters from {{ ref('stg_league') }}
),

preseason_rankings as (
    select * from {{ ref('stg_preseason_rankings') }}
),

draft_day_baseline as (
    select * from {{ ref('int_draft_day_baseline') }}
),

historical_ppg_by_rank as (
    select * from {{ ref('int_historical_ppg_by_rank') }}
),

-- Get replacement levels from frozen baseline
replacement_levels as (
    select
        position,
        replacement_rank,
        -- We'll use preseason projections to estimate replacement PPG
        -- In practice, we'd use projected points from FantasyPros/ESPN
        -- For now, we'll estimate from ADP-based tiers
        vor_multiplier as scarcity_multiplier,
        case
            when position = 'QB' then 18.0  -- QB12 typical projection
            when position = 'RB' then 10.0  -- RB28 typical projection
            when position = 'WR' then 10.0  -- WR32 typical projection
            when position = 'TE' then 8.0   -- TE12 typical projection
        end as estimated_replacement_ppg
    from draft_day_baseline
),

-- Estimate preseason projected PPG using historical averages by rank
-- This uses actual season performance data to build more realistic estimates
-- than hardcoded tiers. Still an approximation until FantasyPros API (task #16)
preseason_with_projected_ppg as (
    select
        pr.*,
        rl.estimated_replacement_ppg,
        rl.scarcity_multiplier,

        -- Use historical averages from actual performance data
        -- Falls back to conservative estimates if no historical data available
        coalesce(
            hpr.smoothed_ppg,
            -- Fallback to conservative position-based estimates
            case
                when pr.position = 'QB' then 18.0
                when pr.position = 'RB' then 12.0
                when pr.position = 'WR' then 11.0
                when pr.position = 'TE' then 8.0
            end
        ) as projected_ppg

    from preseason_rankings as pr
    left join replacement_levels as rl
        on pr.position = rl.position
    left join historical_ppg_by_rank as hpr
        on
            pr.position = hpr.position
            and pr.preseason_rank_position = hpr.rank_position
),

-- Calculate expected VOR for each player based on preseason projections
preseason_expected_vor as (
    select
        player_id,
        player_name,
        position,
        preseason_rank_overall,
        preseason_rank_position,
        preseason_adp,
        projected_ppg,
        estimated_replacement_ppg,
        scarcity_multiplier,

        -- Expected VOR = (Projected PPG - Replacement PPG)
        --                × Expected Games × Scarcity
        -- Assume 15 games played for preseason projections (conservative)
        (projected_ppg - estimated_replacement_ppg)
        * 15
        * scarcity_multiplier as expected_vor,
        (projected_ppg - estimated_replacement_ppg) * 15 as expected_vor_base

    from preseason_with_projected_ppg
    where preseason_adp is not null
),

-- Map players to draft picks based on ADP
-- (In your actual draft, you'd use actual pick numbers)
-- This creates a synthetic "expected draft order" from ADP
draft_pick_mapping as (
    select
        pev.*,
        row_number() over (order by pev.preseason_adp) as pick_no,
        ceil(
            row_number() over (order by pev.preseason_adp) / lc.total_rosters
        ) as round
    from preseason_expected_vor as pev
    cross join league_config as lc
    where pev.preseason_adp <= 150  -- Typical draft depth
),

-- Smooth expected VOR using moving average (LOESS approximation)
-- Window: ±10 picks for stability
smoothed_expected_value as (
    select
        dpm1.pick_no,
        dpm1.round,

        -- Point estimate: median of nearby picks
        percentile_cont(0.5) within group (
            order by dpm2.expected_vor
        ) as expected_vor_at_pick,

        -- Uncertainty bounds: 25th-75th percentile of nearby picks
        percentile_cont(0.25) within group (
            order by dpm2.expected_vor
        ) as expected_vor_p25,

        percentile_cont(0.75) within group (
            order by dpm2.expected_vor
        ) as expected_vor_p75,

        -- Average for comparison
        avg(dpm2.expected_vor) as expected_vor_mean,
        stddev(dpm2.expected_vor) as expected_vor_stddev,

        -- Best available by position at this pick range
        max(case when dpm2.position = 'QB' then dpm2.expected_vor end)
            as best_qb_vor,
        max(case when dpm2.position = 'RB' then dpm2.expected_vor end)
            as best_rb_vor,
        max(case when dpm2.position = 'WR' then dpm2.expected_vor end)
            as best_wr_vor,
        max(case when dpm2.position = 'TE' then dpm2.expected_vor end)
            as best_te_vor,

        -- Count available by position
        count(case when dpm2.position = 'QB' then 1 end) as qb_available,
        count(case when dpm2.position = 'RB' then 1 end) as rb_available,
        count(case when dpm2.position = 'WR' then 1 end) as wr_available,
        count(case when dpm2.position = 'TE' then 1 end) as te_available,

        count(*) as sample_size

    from draft_pick_mapping as dpm1
    cross join draft_pick_mapping as dpm2
    where dpm2.pick_no between dpm1.pick_no - 10 and dpm1.pick_no + 10
    group by dpm1.pick_no, dpm1.round
),

-- Add tier classifications
final as (
    select
        pick_no,
        round,
        expected_vor_at_pick,
        expected_vor_p25,
        expected_vor_p75,
        expected_vor_mean,
        expected_vor_stddev,

        -- Uncertainty range
        best_qb_vor,

        -- Best available by position
        best_rb_vor,
        best_wr_vor,
        best_te_vor,
        qb_available,

        -- Position scarcity at this pick
        rb_available,
        wr_available,
        te_available,
        sample_size,

        -- Value tier
        'FROZEN - Preseason ADP-based' as status,

        -- Recommended position strategy
        expected_vor_p75 - expected_vor_p25 as expected_vor_iqr,

        case
            when expected_vor_at_pick >= 100 then 'ELITE (100+ VOR)'
            when expected_vor_at_pick >= 75 then 'HIGH_VALUE (75-100 VOR)'
            when expected_vor_at_pick >= 50 then 'GOOD_VALUE (50-75 VOR)'
            when expected_vor_at_pick >= 25 then 'MODERATE_VALUE (25-50 VOR)'
            when expected_vor_at_pick >= 10 then 'LOW_VALUE (10-25 VOR)'
            else 'MINIMAL_VALUE (<10 VOR)'
        end as expected_value_tier,

        -- Metadata
        case
            when best_rb_vor > best_wr_vor + 15 then 'PRIORITIZE RB'
            when best_wr_vor > best_rb_vor + 15 then 'PRIORITIZE WR'
            when
                best_te_vor > greatest(best_rb_vor, best_wr_vor) + 20
                then 'PRIORITIZE TE'
            when
                best_qb_vor > greatest(best_rb_vor, best_wr_vor) + 25
                then 'PRIORITIZE QB'
            else 'BALANCED - BPA'
        end as position_recommendation,
        current_timestamp as calculated_at

    from smoothed_expected_value
)

select * from final
order by pick_no
