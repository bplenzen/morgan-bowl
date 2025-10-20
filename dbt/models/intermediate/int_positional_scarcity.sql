{{ config(materialized='table') }}

/*
Positional Scarcity Analysis
Calculates quantitative scarcity multipliers based on drop-off slopes.

Theory: Positions with steeper drop-offs from elite to replacement level are "scarce"
and should be valued higher. RB1 vs RB28 is a bigger gap than QB1 vs QB12.

Scarcity Score = (Elite PPG - Replacement PPG) / Elite PPG
Higher score = More scarce = Higher multiplier on VOR

Replacement levels based on FLEX simulation (greedy allocation by preseason ADP):
- 12 teams × 1 QB = QB12
- 12 teams × (2 RB + 0.33 FLEX) = RB28 (4 of 12 FLEX spots went to RB)
- 12 teams × (2 WR + 0.67 FLEX) = WR32 (8 of 12 FLEX spots went to WR)
- 12 teams × 1 TE = TE12 (0 FLEX spots went to TE in PPR)

Example:
- TE: (16.0 - 8.4) / 16.0 = 0.475 (47.5% drop-off) = MOST SCARCE
- RB: (24.2 - 13.7) / 24.2 = 0.432 (43.2% drop-off) = SCARCE
- WR: (21.4 - 13.5) / 21.4 = 0.369 (36.9% drop-off) = MODERATE
- QB: (25.0 - 15.8) / 25.0 = 0.367 (36.7% drop-off) = MODERATE
*/

with current_rankings as (
    select * from {{ ref('int_current_player_rankings') }}
),

-- Calculate key percentiles for each position
position_benchmarks as (
    select
        position,

        -- Elite tier (top player)
        max(case when current_rank_position = 1 then points_per_game end)
            as elite_ppg,

        -- Top 5 average
        avg(case when current_rank_position <= 5 then points_per_game end)
            as top5_avg_ppg,

        -- Replacement level: QB12, RB28, WR32, TE12 (based on FLEX simulation)
        -- FLEX allocation: 4 RB, 8 WR, 0 TE (greedy fill by preseason ADP)
        max(case
            when
                position = 'QB' and current_rank_position = 12
                then points_per_game
            when
                position = 'TE' and current_rank_position = 12
                then points_per_game
            when
                position = 'RB' and current_rank_position = 28
                then points_per_game
            when
                position = 'WR' and current_rank_position = 32
                then points_per_game
        end) as replacement_ppg,

        -- Depth level (RB36, WR36 for FLEX consideration)
        max(case
            when
                position in ('RB', 'WR') and current_rank_position = 36
                then points_per_game
        end) as depth_ppg,

        -- Waiver wire level (RB48, WR48)
        max(case
            when
                position in ('RB', 'WR') and current_rank_position = 48
                then points_per_game
        end) as waiver_ppg

    from current_rankings
    where position in ('QB', 'RB', 'WR', 'TE')
    group by position
),

-- Calculate scarcity metrics
scarcity_calculations as (
    select
        position,
        elite_ppg,
        top5_avg_ppg,
        replacement_ppg,
        depth_ppg,
        waiver_ppg,

        -- Primary scarcity score: Elite to replacement drop-off
        case
            when elite_ppg > 0
                then
                    (elite_ppg - replacement_ppg) / elite_ppg
            else 0
        end as scarcity_score,

        -- Secondary: Top 5 to replacement (more stable)
        case
            when top5_avg_ppg > 0
                then
                    (top5_avg_ppg - replacement_ppg) / top5_avg_ppg
            else 0
        end as scarcity_score_top5,

        -- Depth drop-off (replacement to waiver)
        case
            when replacement_ppg > 0 and waiver_ppg is not null
                then
                    (replacement_ppg - waiver_ppg) / replacement_ppg
        end as depth_dropoff,

        -- Absolute point differential
        elite_ppg - replacement_ppg as elite_gap,
        replacement_ppg - coalesce(waiver_ppg, 0) as replacement_gap

    from position_benchmarks
),

-- Apply scarcity multipliers
final as (
    select
        *,

        -- Scarcity tier (for categorical analysis)
        case
            when scarcity_score >= 0.45 then 'VERY_SCARCE'
            when scarcity_score >= 0.40 then 'SCARCE'
            when scarcity_score >= 0.35 then 'MODERATE'
            else 'PLENTIFUL'
        end as scarcity_tier,

        -- VOR multiplier (1.0 baseline)
        -- More scarce positions get higher multiplier
        case
            when scarcity_score >= 0.45 then 1.30  -- TE: 30% VOR boost
            when scarcity_score >= 0.40 then 1.20  -- RB: 20% VOR boost
            when scarcity_score >= 0.35 then 1.05  -- WR: 5% VOR boost
            else 1.00  -- QB: No boost
        end as vor_multiplier,

        -- Draft priority score (0-100)
        -- Combines scarcity with depth dropoff
        round(
            (scarcity_score * 70)  -- Scarcity worth 70 points
            + (coalesce(depth_dropoff, 0) * 30),  -- Depth worth 30 points
            1
        ) as draft_priority_score,

        -- Positional value index (normalized 0-100)
        -- Higher = more valuable position to draft
        round(
            100 * (
                scarcity_score
                / (select max(scarcity_score) from scarcity_calculations)
            ),
            1
        ) as positional_value_index

    from scarcity_calculations
)

select * from final
order by scarcity_score desc
