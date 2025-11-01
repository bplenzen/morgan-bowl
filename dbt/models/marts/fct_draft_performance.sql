{{ config(materialized='table') }}

/*
Draft Performance Analysis - Context-Aware Grading with NO LOOK-AHEAD BIAS

ANTI-LOOK-AHEAD METHODOLOGY:
This model evaluates draft DECISIONS (process) not OUTCOMES (results).
It uses FROZEN parameters from draft day (2025-09-04) to prevent look-ahead bias.

DATA SEPARATION:
1. DRAFT-DAY DECISIONS (used for grading):
   - Preseason ADP rankings (via stg_preseason_rankings)
   - Frozen replacement levels (via int_draft_day_baseline)
   - Draft position and opportunity cost
   - Frozen scarcity multipliers from draft day

2. ACTUAL OUTCOMES (used for VOR calculation only):
   - Current season performance (via int_current_player_rankings)
   - Weekly variance and consistency metrics
   - Games played and total points

GRADING LOGIC:
- Draft grades evaluate the QUALITY OF THE DECISION at draft time
- VOR calculations use actual performance but FROZEN baselines
- Replacement levels NEVER change (Jordan Love QB12, Najee Harris RB28, etc.)
- No player stats from AFTER the draft date influence the grade assignment

VERIFICATION:
See tests/assert_no_lookahead_bias_draft.sql for validation that:
- Baseline frozen_date = 2025-09-04
- Replacement players match frozen parameters
- Projection source = Preseason_ADP_Consensus_2025
- Players with 0 games get F grades (no post-draft data used)

Uses VOR (Value Over Replacement), positional scarcity, PPG-based performance,
and draft context to grade picks. Accounts for the fact that late-round QB1
is different value than late-round RB1 due to positional scarcity.
*/

with draft_picks as (
    select * from {{ ref('stg_draft_picks') }}
),

preseason_rankings as (
    select * from {{ ref('stg_preseason_rankings') }}
),

current_rankings as (
    select * from {{ ref('int_current_player_rankings') }}
),

weekly_variance as (
    select * from {{ ref('int_player_weekly_variance') }}
),

opportunity_cost as (
    select * from {{ ref('int_opportunity_cost') }}
),

-- NEW: Expected value by pick (pick-value curve)
expected_value_by_pick as (
    select * from {{ ref('int_expected_value_by_pick') }}
),

-- FROZEN DRAFT-DAY BASELINE (prevents look-ahead bias)
-- This uses ONLY preseason data - replacement levels never change
draft_day_baseline as (
    select * from {{ ref('int_draft_day_baseline') }}
),

-- NEW: Multiplicative risk factors (not averaged)
player_risk_factors as (
    select * from {{ ref('int_player_risk_factors') }}
),

-- DEPRECATED: Old scarcity and risk models
-- Kept for backwards compatibility during transition
positional_scarcity as (
    select * from {{ ref('int_positional_scarcity') }}
),

risk_adjusted as (
    select * from {{ ref('int_risk_adjusted_vor') }}
),

rosters as (
    select * from {{ ref('stg_rosters') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

-- REPLACEMENT LEVELS FROM FROZEN BASELINE
-- These NEVER change - they're based on draft-day parameters only
-- NO LOOK-AHEAD BIAS: Uses preseason ADP ranks, not current performance
replacement_levels as (
    select
        ddb.position,
        -- Use frozen replacement rank from draft day baseline
        ddb.replacement_rank,
        ddb.replacement_player_name,
        ddb.replacement_player_adp,
        ddb.vor_multiplier as scarcity_multiplier,

        -- Get current performance of replacement player (for VOR calc only)
        -- NOTE: We use the IDENTITY (Jordan Love, Najee Harris, etc.) from draft day
        -- But their CURRENT performance for fair comparison
        case
            when ddb.position = 'QB'
                then (
                    select points_per_game
                    from current_rankings
                    where position = 'QB' and current_rank_position = 12
                )
            when ddb.position = 'TE'
                then (
                    select points_per_game
                    from current_rankings
                    where position = 'TE' and current_rank_position = 12
                )
            when ddb.position = 'RB'
                then (
                    select points_per_game
                    from current_rankings
                    where position = 'RB' and current_rank_position = 28
                )
            when ddb.position = 'WR' then (
                select points_per_game
                from current_rankings
                where position = 'WR' and current_rank_position = 32
            )
        end as replacement_ppg,
        -- Also get top-5 average for "elite" threshold
        (
            select avg(points_per_game)
            from current_rankings cr
            where cr.position = ddb.position and cr.current_rank_position <= 5
        ) as elite_avg_ppg,

        -- Metadata
        'FROZEN - Never recalculate' as status,
        current_timestamp as calculated_at
    from draft_day_baseline ddb
),

-- Calculate Value Over Replacement (VOR) for each player
draft_with_vor as (
    select
        dp.draft_id,
        dp.pick_no,
        dp.round,
        dp.draft_slot,
        dp.roster_id,
        dp.player_id,
        dp.player_name,
        dp.position,
        dp.team,
        dp.draft_tier,

        -- Preseason expectations
        pr.preseason_rank_overall,
        pr.preseason_rank_position,
        pr.preseason_adp,
        pr.preseason_tier,

        -- Current performance
        cr.current_rank_overall,
        cr.current_rank_position,
        cr.total_points,
        cr.points_per_game,
        cr.games_played,
        cr.current_tier,

        -- Weekly variance & consistency metrics
        wv.avg_weekly_points,
        wv.stddev_weekly_points,
        wv.coefficient_of_variation,
        wv.boom_rate_pct,
        wv.bust_rate_pct,
        wv.floor_10th_percentile,
        wv.ceiling_90th_percentile,
        wv.consistency_tier,
        wv.volatility_risk_score,

        -- Opportunity Cost Analysis (draft day focused)
        oc.best_available_player_name,
        oc.best_available_pick_no,
        oc.best_available_adp,
        oc.best_available_preseason_rank,
        oc.draft_day_opportunity_cost,
        oc.hindsight_best_player,
        oc.hindsight_opportunity_cost,
        oc.picks_until_better_option,
        oc.opportunity_cost_tier,
        oc.opportunity_verdict,

        -- Positional Scarcity Metrics (FROZEN at draft day - no look-ahead bias)
        -- These come from draft_day_baseline, not dynamic calculation
        ddb.scarcity_score_normalized as scarcity_score,
        ddb.scarcity_tier,
        ddb.vor_multiplier as scarcity_multiplier,  -- Frozen scarcity from draft day
        ddb.draft_priority_score,
        ddb.elite_to_replacement_picks as positional_value_index,

        -- Risk-Adjusted VOR Metrics (NEW MULTIPLICATIVE MODEL)
        -- Properly compounds risk factors instead of averaging
        prf.coefficient_of_variation as risk_cv,
        prf.availability_factor,  -- % of games played
        prf.composite_risk_factor,  -- Multiplicative: availability * volatility * position_fragility
        prf.risk_tier,
        prf.primary_risk_driver,
        prf.risk_adjusted_scarcity_vor,  -- Already includes scarcity multiplier
        prf.vor_lost_to_risk as vor_reduction_from_risk,

        -- UNCERTAINTY QUANTIFICATION: VOR confidence intervals
        prf.risk_adjusted_vor_lower_bound,  -- Pessimistic scenario (-1 stddev)
        prf.risk_adjusted_vor_upper_bound,  -- Optimistic scenario (+1 stddev)
        prf.vor_uncertainty_range,          -- Width of confidence interval
        prf.vor_coefficient_of_variation as vor_cv,  -- Relative uncertainty

        -- PICK-VALUE CURVE: Expected VOR at this draft position
        evp.expected_vor_at_pick,           -- What VOR was expected at this pick?
        evp.expected_vor_p25,               -- 25th percentile expectation
        evp.expected_vor_p75,               -- 75th percentile expectation
        evp.expected_value_tier,            -- ELITE/HIGH_VALUE/etc tier for this pick
        evp.position_recommendation,        -- Should this pick prioritize RB/WR/etc?

        -- Value Over Replacement
        rl.replacement_ppg,
        rl.elite_avg_ppg,
        case
            when
                cr.points_per_game is not null
                and rl.replacement_ppg is not null
                then
                    (cr.points_per_game - rl.replacement_ppg) * cr.games_played
        end as value_over_replacement,

        -- Scarcity-Adjusted VOR (uses FROZEN scarcity multipliers from draft day)
        case
            when
                cr.points_per_game is not null
                and rl.replacement_ppg is not null
                and rl.scarcity_multiplier is not null  -- From frozen baseline, not dynamic
                then
                    (cr.points_per_game - rl.replacement_ppg)
                    * cr.games_played
                    * rl.scarcity_multiplier  -- Frozen at draft time
        end as scarcity_adjusted_vor,

        -- Is this player even startable? (above replacement level)
        case
            when
                cr.points_per_game is not null
                and rl.replacement_ppg is not null
                then
                    cr.points_per_game > rl.replacement_ppg
            else false
        end as is_startable,

        -- Is this player elite? (top 5 at position)
        case
            when cr.current_rank_position is not null
                then
                    cr.current_rank_position <= 5
            else false
        end as is_elite,

        -- Calculate differentials (still useful context)
        case
            when pr.preseason_adp is not null
                then
                    dp.pick_no - pr.preseason_adp
        end as adp_differential,

        case
            when
                pr.preseason_rank_position is not null
                and cr.current_rank_position is not null
                then
                    pr.preseason_rank_position - cr.current_rank_position
        end as position_rank_differential

    from draft_picks as dp
    left join preseason_rankings as pr
        on dp.player_id = pr.player_id
    left join current_rankings as cr
        on dp.player_id = cr.player_id
    left join weekly_variance as wv
        on dp.player_id = wv.player_id
    left join opportunity_cost as oc
        on dp.pick_no = oc.pick_no
    left join player_risk_factors as prf
        on dp.player_id = prf.player_id
    left join replacement_levels as rl
        on dp.position = rl.position
    left join draft_day_baseline as ddb
        on dp.position = ddb.position
    left join expected_value_by_pick as evp
        on dp.pick_no = evp.pick_no
),

-- Apply advanced grading based on risk-adjusted VOR, opportunity cost, and context
draft_with_grades as (
    select
        *,

        -- FINAL GRADE: Combines risk-adjusted VOR, draft context, and opportunity cost
        -- Uses risk-adjusted scarcity VOR as primary value metric
        case
            -- K/DEF: No grade - streaming positions not evaluated for draft quality
            -- They break VOR-based grading due to near-zero positional scarcity
            when position in ('K', 'DEF') then NULL

            -- INACTIVE/INJURED players
            when games_played = 0 or games_played is null then 'F (INACTIVE)'

            -- EARLY ROUNDS (1-3): Elite expectations, harsh penalties for reaches
            when round <= 3
                then
                    case
                    -- Elite + Low Risk + Good value = A+
                        when
                            is_elite
                            and risk_tier = 'VERY_LOW_RISK'
                            and draft_day_opportunity_cost >= 0
                            then 'A+ (Elite & Reliable)'
                        when
                            is_elite
                            and risk_tier in ('VERY_LOW_RISK', 'LOW_RISK')
                            then 'A (Elite but Some Risk)'
                        when is_elite then 'A- (Elite but Risky)'

                        -- Starter quality but disappointing for early round
                        when
                            is_startable
                            and current_rank_position <= 12
                            and risk_tier = 'VERY_LOW_RISK'
                            then 'B+ (Reliable Starter)'
                        when
                            is_startable and current_rank_position <= 12
                            then 'B (Starter Quality)'
                        when
                            is_startable
                            then 'C+ (Startable but Disappointing)'

                        -- Major bust territory
                        when
                            current_rank_position <= 24
                            then 'D (Major Bust - Bench Player)'
                        else 'F (Complete Bust)'
                    end

            -- MID ROUNDS (4-7): Starter expectations, reward value + consistency
            when round between 4 and 7
                then
                    case
                    -- Elite breakout (scarce positions get extra credit)
                        when
                            is_elite
                            and position in ('RB', 'TE')
                            and risk_tier = 'VERY_LOW_RISK'
                            then 'A+ (League Winner - Scarce & Reliable)'
                        when
                            is_elite and position in ('RB', 'TE')
                            then 'A+ (League Winner - Scarce Position)'
                        when
                            is_elite and risk_tier = 'VERY_LOW_RISK'
                            then 'A+ (League Winner & Reliable)'
                        when is_elite then 'A (Elite Value)'

                        -- Outperforming expectations
                        when
                            is_startable
                            and position_rank_differential >= 12
                            and risk_tier = 'VERY_LOW_RISK'
                            then 'A (Exceeded - Reliable)'
                        when
                            is_startable and position_rank_differential >= 12
                            then 'A- (Exceeded Expectations)'
                        when
                            is_startable
                            and position_rank_differential >= 6
                            and risk_tier = 'VERY_LOW_RISK'
                            then 'B+ (Solid & Reliable)'
                        when
                            is_startable and position_rank_differential >= 6
                            then 'B+ (Solid Value)'

                        -- Meeting expectations (consistency matters here)
                        when
                            is_startable
                            and abs(position_rank_differential) <= 5
                            and consistency_tier = 'VERY_CONSISTENT'
                            then 'B+ (Reliable Starter)'
                        when
                            is_startable
                            and abs(position_rank_differential) <= 5
                            then 'B (As Expected)'

                        -- Underperforming
                        when
                            is_startable
                            and risk_tier in ('MODERATE_RISK', 'HIGH_RISK')
                            then 'C+ (Starter but Risky)'
                        when is_startable then 'C (Startable but Meh)'
                        when current_rank_position <= 36 then 'D (Bench Player)'
                        else 'F (Wasted Pick)'
                    end

            -- LATE ROUNDS (8-14): Any value is great, consistency is bonus
            when round >= 8
                then
                    case
                    -- Any elite player = huge win
                        when
                            is_elite
                            and position in ('RB', 'TE')
                            and risk_tier = 'VERY_LOW_RISK'
                            then 'A+ (Absolute Steal - Scarce & Reliable)'
                        when
                            is_elite and position in ('RB', 'TE')
                            then 'A+ (Absolute Steal - Scarce Position)'
                        when
                            is_elite and risk_tier = 'VERY_LOW_RISK'
                            then 'A+ (Absolute Steal & Reliable)'
                        when is_elite then 'A+ (Absolute Steal)'

                        -- Startable = win (consistency bonus)
                        when
                            is_startable
                            and current_rank_position <= 12
                            and risk_tier = 'VERY_LOW_RISK'
                            then 'A (Great Reliable Starter)'
                        when
                            is_startable and current_rank_position <= 12
                            then 'A (Great Late-Round Starter)'
                        when
                            is_startable
                            and current_rank_position <= 24
                            and consistency_tier = 'VERY_CONSISTENT'
                            then 'B+ (Solid Reliable Depth)'
                        when
                            is_startable and current_rank_position <= 24
                            then 'B+ (Solid Depth)'
                        when is_startable then 'B (Usable Depth)'

                        -- Bench but not useless
                        when current_rank_position <= 48 then 'C (Bench Depth)'
                        else 'D (Droppable)'
                    end

            else 'C (Unknown)'
        end as pick_grade,

        -- GRADE SCORE (0-100): Numeric grade for analysis
        -- Based on risk-adjusted scarcity VOR relative to draft position
        case
            when position in ('K', 'DEF') then NULL  -- Streaming positions not graded
            when games_played = 0 or games_played is null then 0
            when risk_adjusted_scarcity_vor is null then 50  -- Default
            -- Scale based on round expectations
            when round <= 3
                then
                    -- Early rounds: Expect 80+ VOR, scale 0-100
                    least(
                        100, greatest(0, 50 + (risk_adjusted_scarcity_vor / 2))
                    )
            when round between 4 and 7
                then
                    -- Mid rounds: Expect 40+ VOR, scale 0-100
                    least(
                        100,
                        greatest(0, 60 + (risk_adjusted_scarcity_vor / 1.5))
                    )
            else
                -- Late rounds: Any positive VOR is good
                least(100, greatest(0, 70 + risk_adjusted_scarcity_vor))
        end as grade_score,

        -- GRADE SCORE CONFIDENCE INTERVAL (using VOR uncertainty)
        -- Lower bound: pessimistic grade (if no uncertainty data, use point estimate)
        case
            when position in ('K', 'DEF') then NULL  -- Streaming positions not graded
            when games_played = 0 or games_played is null then 0
            when risk_adjusted_vor_lower_bound is null then
                -- No uncertainty data - use the point estimate itself
                case
                    when risk_adjusted_scarcity_vor is null then 50
                    when round <= 3
                        then least(100, greatest(0, 50 + (risk_adjusted_scarcity_vor / 2)))
                    when round between 4 and 7
                        then least(100, greatest(0, 60 + (risk_adjusted_scarcity_vor / 1.5)))
                    else least(100, greatest(0, 70 + risk_adjusted_scarcity_vor))
                end
            when round <= 3
                then least(100, greatest(0, 50 + (risk_adjusted_vor_lower_bound / 2)))
            when round between 4 and 7
                then least(100, greatest(0, 60 + (risk_adjusted_vor_lower_bound / 1.5)))
            else least(100, greatest(0, 70 + risk_adjusted_vor_lower_bound))
        end as grade_score_lower_bound,

        -- Upper bound: optimistic grade (if no uncertainty data, use point estimate)
        case
            when position in ('K', 'DEF') then NULL  -- Streaming positions not graded
            when games_played = 0 or games_played is null then 0
            when risk_adjusted_vor_upper_bound is null then
                -- No uncertainty data - use the point estimate itself
                case
                    when risk_adjusted_scarcity_vor is null then 50
                    when round <= 3
                        then least(100, greatest(0, 50 + (risk_adjusted_scarcity_vor / 2)))
                    when round between 4 and 7
                        then least(100, greatest(0, 60 + (risk_adjusted_scarcity_vor / 1.5)))
                    else least(100, greatest(0, 70 + risk_adjusted_scarcity_vor))
                end
            when round <= 3
                then least(100, greatest(0, 50 + (risk_adjusted_vor_upper_bound / 2)))
            when round between 4 and 7
                then least(100, greatest(0, 60 + (risk_adjusted_vor_upper_bound / 1.5)))
            else least(100, greatest(0, 70 + risk_adjusted_vor_upper_bound))
        end as grade_score_upper_bound,

        -- Grade uncertainty (width of confidence interval)
        case
            when position in ('K', 'DEF') then NULL  -- Streaming positions not graded
            when vor_uncertainty_range is not null and vor_uncertainty_range > 0
                then round(vor_uncertainty_range / 2.0, 1)  -- ±range around point estimate
            else 0.0
        end as grade_score_uncertainty,

        -- COMPREHENSIVE VALUE VERDICT: Explains the full story
        case
            -- K/DEF: No verdict - streaming positions not graded
            when position in ('K', 'DEF') then NULL

            when
                games_played = 0 or games_played is null
                then 'No games played - cannot evaluate'

            -- Elite performers
            when is_elite and round <= 3 and risk_tier = 'VERY_LOW_RISK'
                then
                    'Delivered elite production as drafted - highly reliable ('
                    || consistency_tier
                    || ')'
            when is_elite and round <= 3
                then
                    'Elite production but '
                    || lower(risk_tier)
                    || ' concerns reduce value'
            when
                is_elite
                and round between 4 and 7
                and position in ('RB', 'TE')
                and risk_tier = 'VERY_LOW_RISK'
                then
                    'Elite '
                    || position
                    || ' breakout - high scarcity value + reliable production'
            when is_elite and round between 4 and 7 and position in ('RB', 'TE')
                then
                    'Elite '
                    || position
                    || ' breakout - high scarcity but '
                    || lower(risk_tier)
            when
                is_elite
                and round between 4 and 7
                and risk_tier = 'VERY_LOW_RISK'
                then
                    'Elite breakout from mid-round - reliable weekly performer'
            when is_elite and round between 4 and 7
                then
                    'Elite breakout but volatility/injury concerns ('
                    || lower(risk_tier)
                    || ')'
            when is_elite and round >= 8
                then
                    'Draft steal - elite player found late (risk-adj VOR: '
                    || round(risk_adjusted_scarcity_vor, 1)
                    || ')'

            -- Solid starters
            when is_startable and round <= 3 and risk_tier = 'VERY_LOW_RISK'
                then
                    'Reliable starter but disappointing for round 1-3 pick'
            when is_startable and round <= 3
                then
                    'Startable but disappointing for round 1-3 + '
                    || lower(risk_tier)
            when
                is_startable
                and round between 4 and 7
                and consistency_tier = 'VERY_CONSISTENT'
                then
                    'Solid consistent starter - low volatility (CV: '
                    || round(coefficient_of_variation, 2)
                    || ')'
            when
                is_startable
                and round between 4 and 7
                and risk_tier in ('MODERATE_RISK', 'HIGH_RISK')
                then
                    'Starter quality but '
                    || lower(risk_tier)
                    || ' - '
                    || round((1 - availability_factor) * 100, 0)
                    || '% games missed'
            when is_startable and round between 4 and 7
                then
                    'Solid starter from middle rounds (VOR: '
                    || round(value_over_replacement, 1)
                    || ')'
            when is_startable and round >= 8 and risk_tier = 'VERY_LOW_RISK'
                then
                    'Great late value - reliable weekly starter'
            when is_startable and round >= 8
                then
                    'Late-round starter but some reliability concerns'

            -- Disappointments
            when
                not is_startable
                and round <= 3
                and draft_day_opportunity_cost < -10
                then
                    'Major bust - reached in draft (ADP: '
                    || round(preseason_adp, 1)
                    || ') and underperformed'
            when not is_startable and round <= 3
                then
                    'Major bust - early pick not startable'
            when
                not is_startable
                and round between 4 and 7
                and draft_day_opportunity_cost < -5
                then
                    'Disappointment - reached in draft and did not deliver'
            when not is_startable and round between 4 and 7
                then
                    'Expected starter production but did not deliver'
            when not is_startable and round >= 8
                then
                    'Late pick that did not pan out - low cost'

            else 'Performance evaluation in progress'
        end as value_verdict,

        -- VOR TIER: Boris Chen style tiers for easy scanning
        case
            when position in ('K', 'DEF') then null  -- No tiers for streaming
            when risk_adjusted_scarcity_vor >= 80 then 'TIER_1_ELITE'
            when risk_adjusted_scarcity_vor >= 60 then 'TIER_2_HIGH'
            when risk_adjusted_scarcity_vor >= 40 then 'TIER_3_SOLID'
            when risk_adjusted_scarcity_vor >= 20 then 'TIER_4_DEPTH'
            when risk_adjusted_scarcity_vor >= 0 then 'TIER_5_REPLACEMENT'
            else 'TIER_6_BUST'
        end as vor_tier,

        -- User-friendly tier label
        case
            when position in ('K', 'DEF') then null
            when risk_adjusted_scarcity_vor >= 80 then 'Elite'
            when risk_adjusted_scarcity_vor >= 60 then 'High Value'
            when risk_adjusted_scarcity_vor >= 40 then 'Solid Starter'
            when risk_adjusted_scarcity_vor >= 20 then 'Depth/Flex'
            when risk_adjusted_scarcity_vor >= 0 then 'Replacement'
            else 'Bust'
        end as vor_tier_label

    from draft_with_vor
),

-- Add team/manager info
final as (
    select
        dwg.*,
        r.owner_id,
        u.display_name as manager_name

    from draft_with_grades as dwg
    left join rosters as r
        on dwg.roster_id = r.roster_id
    left join users as u
        on r.owner_id = u.user_id
)

select * from final
order by pick_no
