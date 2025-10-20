{{ config(materialized='table') }}

/*
Draft Performance Analysis - Context-Aware Grading
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

-- Calculate replacement level PPG for each position
-- Based on FLEX simulation (greedy allocation by preseason ADP):
-- - QB12 (12 teams × 1 QB)
-- - RB28 (12 teams × 2 RB + 4 FLEX spots)
-- - WR32 (12 teams × 2 WR + 8 FLEX spots)
-- - TE12 (12 teams × 1 TE + 0 FLEX spots)
replacement_levels as (
    select
        position,
        case
            when position = 'QB'
                then (
                    select points_per_game
                    from current_rankings
                    where position = 'QB' and current_rank_position = 12
                )
            when position = 'TE'
                then (
                    select points_per_game
                    from current_rankings
                    where position = 'TE' and current_rank_position = 12
                )
            when position = 'RB'
                then (
                    select points_per_game
                    from current_rankings
                    where position = 'RB' and current_rank_position = 28
                )
            when position = 'WR' then (
                select points_per_game
                from current_rankings
                where position = 'WR' and current_rank_position = 32
            )
        end as replacement_ppg,
        -- Also get top-5 average for "elite" threshold
        (
            select avg(points_per_game)
            from current_rankings
            where position = cr.position and current_rank_position <= 5
        ) as elite_avg_ppg
    from (select distinct position from current_rankings) as cr
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

        -- Positional Scarcity Metrics
        ps.scarcity_score,
        ps.scarcity_tier,
        ps.vor_multiplier,
        ps.draft_priority_score,
        ps.positional_value_index,

        -- Risk-Adjusted VOR Metrics
        ra.coefficient_of_variation as risk_cv,
        ra.games_missed_pct,
        ra.composite_risk_penalty,
        ra.risk_tier,
        ra.risk_adjusted_vor,
        ra.risk_adjusted_scarcity_vor,
        ra.vor_reduction_from_risk,

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

        -- Scarcity-Adjusted VOR (accounts for positional scarcity)
        case
            when
                cr.points_per_game is not null
                and rl.replacement_ppg is not null
                and ps.vor_multiplier is not null
                then
                    (cr.points_per_game - rl.replacement_ppg)
                    * cr.games_played
                    * ps.vor_multiplier
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
    left join positional_scarcity as ps
        on dp.position = ps.position
    left join risk_adjusted as ra
        on dp.player_id = ra.player_id
    left join replacement_levels as rl
        on dp.position = rl.position
),

-- Apply advanced grading based on risk-adjusted VOR, opportunity cost, and context
draft_with_grades as (
    select
        *,

        -- FINAL GRADE: Combines risk-adjusted VOR, draft context, and opportunity cost
        -- Uses risk-adjusted scarcity VOR as primary value metric
        case
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

        -- COMPREHENSIVE VALUE VERDICT: Explains the full story
        case
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
                    || round(games_missed_pct, 0)
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
        end as value_verdict

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
