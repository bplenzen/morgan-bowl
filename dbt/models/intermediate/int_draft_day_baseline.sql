{{ config(materialized='table') }}

/*
Draft Day Baseline - FROZEN Parameters for Draft Analysis

This model provides FROZEN replacement levels and scarcity multipliers
based ONLY on preseason data available at draft time. These values
NEVER change when new weeks are ingested - preventing look-ahead bias.

CRITICAL: This model uses PRESEASON rankings ONLY, not current season performance.
This ensures draft grades evaluate the PROCESS (draft-day decisions) not OUTCOMES.

Methodology:
- Uses preseason ADP as proxy for expert consensus projections
- ADP aggregates FantasyPros, ESPN, Yahoo, and market sentiment
- FLEX simulation uses greedy algorithm by ADP (not current performance)
- Replacement levels frozen at draft time (2025-09-04)
- Scarcity multipliers based on preseason elite-to-replacement drop-off

See: data/draft_day_parameters_2025.yml for frozen parameter values
*/

with preseason_rankings as (
    select * from {{ ref('stg_preseason_rankings') }}
),

-- FROZEN replacement player identities (from parameter file)
-- These are the actual players who define the replacement level
-- QB12, RB28, WR32, TE12 based on preseason ADP
replacement_players as (
    select
        'QB' as position,
        12 as replacement_rank,
        '6790' as player_id,  -- Jordan Love
        'Jordan Love' as player_name,
        96.0 as replacement_adp
    union all
    select
        'RB' as position,
        28 as replacement_rank,
        '7528' as player_id,  -- Najee Harris
        'Najee Harris' as player_name,
        89.0 as replacement_adp
    union all
    select
        'WR' as position,
        32 as replacement_rank,
        -- Jordan Addison (WR30 in file, but using rank 32 for FLEX)
        '9488' as player_id,
        'Jordan Addison' as player_name,
        104.0 as replacement_adp
    union all
    select
        'TE' as position,
        12 as replacement_rank,
        '7039' as player_id,  -- Cole Kmet
        'Cole Kmet' as player_name,
        144.0 as replacement_adp
),

-- Calculate preseason benchmarks for each position
-- Using ONLY preseason data - no current season performance
preseason_benchmarks as (
    select
        position,

        -- Elite tier (top player by preseason ADP)
        min(case when preseason_rank_position = 1 then preseason_adp end)
            as elite_adp,

        -- Top 5 average ADP (lower is better)
        avg(case when preseason_rank_position <= 5 then preseason_adp end)
            as top5_avg_adp,

        -- Replacement level ADP from our frozen parameters
        max(case
            when
                position = 'QB' and preseason_rank_position = 12
                then preseason_adp
            when
                position = 'TE' and preseason_rank_position = 12
                then preseason_adp
            when
                position = 'RB' and preseason_rank_position = 28
                then preseason_adp
            when
                position = 'WR' and preseason_rank_position = 32
                then preseason_adp
        end) as replacement_adp,

        -- Elite player name (for reference)
        min(case when preseason_rank_position = 1 then player_name end)
            as elite_player_name,

        -- Count of players at position (for validation)
        count(*) as total_players

    from preseason_rankings
    where position in ('QB', 'RB', 'WR', 'TE')
    group by position
),

-- Calculate FROZEN scarcity scores based on preseason data only
-- Higher ADP number = worse value = closer to replacement
-- Scarcity = (Elite ADP - Replacement ADP) / Elite ADP won't work (lower is better for ADP)
-- Instead: Measure draft capital spread
scarcity_calculations as (
    select
        position,
        elite_adp,
        top5_avg_adp,
        replacement_adp,
        elite_player_name,
        total_players,

        -- Calculate scarcity based on draft capital spread
        -- In ADP, lower number = higher value
        -- Scarcity = how many picks separate elite from replacement
        -- Normalize by total draft capital (assume 180 pick draft, 15 rounds)
        case
            when elite_adp is not null and replacement_adp is not null
                then (replacement_adp - elite_adp) / 180.0
            else 0
        end as scarcity_score_normalized,

        -- Raw pick spread
        case
            when elite_adp is not null and replacement_adp is not null
                then replacement_adp - elite_adp
            else 0
        end as elite_to_replacement_picks

    from preseason_benchmarks
),

-- Apply FROZEN scarcity multipliers from parameter file
-- These multipliers are based on preseason analysis and NEVER change
final_baseline as (
    select
        sc.*,

        -- Scarcity tier (for categorical analysis)
        '2025-09-04' as frozen_date,

        -- FROZEN VOR multipliers from parameter file
        -- These are the values that were calculated at draft time
        'Preseason_ADP_Consensus_2025' as projection_source,

        -- Draft priority score (0-100)
        -- Based on scarcity and importance
        'FROZEN - Never recalculate' as status,

        -- Add frozen parameter metadata
        case
            when sc.scarcity_score_normalized >= 0.45 then 'VERY_SCARCE'
            when sc.scarcity_score_normalized >= 0.35 then 'SCARCE'
            when sc.scarcity_score_normalized >= 0.25 then 'MODERATE'
            else 'PLENTIFUL'
        end as scarcity_tier,
        case
            when sc.position = 'TE' then 1.30  -- Most scarce
            when sc.position = 'RB' then 1.20  -- Very scarce
            when sc.position = 'WR' then 1.05  -- Moderate
            when sc.position = 'QB' then 1.00  -- Baseline
        end as vor_multiplier,
        round(sc.scarcity_score_normalized * 100, 1) as draft_priority_score

    from scarcity_calculations as sc
),

-- Add replacement player details
with_replacement_details as (
    select
        fb.*,
        rp.replacement_rank,
        rp.player_id as replacement_player_id,
        rp.player_name as replacement_player_name,
        rp.replacement_adp as replacement_player_adp
    from final_baseline as fb
    left join replacement_players as rp on fb.position = rp.position
)

select * from with_replacement_details
order by vor_multiplier desc, position asc
