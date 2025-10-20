{{ config(materialized='table') }}

/*
DRAFT REALIZED VALUE ANALYSIS
Outcome-based hindsight report showing actual player value vs draft position

PHILOSOPHY:
This is SEPARATE from fct_draft_performance (process-based grading).

fct_draft_performance = "Was this a SMART draft decision at the time?"
  - Uses FROZEN draft-day parameters
  - Grades process quality
  - Never changes when new weeks added

fct_draft_realized_value = "What VALUE did this pick actually deliver?"
  - Uses CURRENT season performance
  - Shows actual outcomes
  - Updates as season progresses

Both are valuable! Process ≠ Outcome.
Good process can have bad luck. Bad process can get lucky.

EXAMPLE:
Player drafted as RB12 (reasonable) but got injured Week 2 (unlucky)
- Process Grade: B+ (smart draft-day decision)
- Realized Value: F (injury killed value)
- Conclusion: Good process, bad outcome (unlucky)

This model shows the "bad outcome" part. fct_draft_performance shows "good process" part.
*/

with draft_picks as (
    select * from {{ ref('stg_draft_picks') }}
),

-- CURRENT season performance (updates weekly)
current_performance as (
    select * from {{ ref('int_current_player_rankings') }}
),

-- CURRENT replacement levels (dynamic, based on actual performance)
-- This is INTENTIONALLY different from frozen draft-day baseline
current_replacement_levels as (
    select
        position,

        -- Current replacement level PPG (based on actual season performance)
        case
            when position = 'QB'
                then (
                    select points_per_game
                    from current_performance
                    where position = 'QB' and current_rank_position = 12
                )
            when position = 'TE'
                then (
                    select points_per_game
                    from current_performance
                    where position = 'TE' and current_rank_position = 12
                )
            when position = 'RB'
                then (
                    select points_per_game
                    from current_performance
                    where position = 'RB' and current_rank_position = 28
                )
            when position = 'WR'
                then (
                    select points_per_game
                    from current_performance
                    where position = 'WR' and current_rank_position = 32
                )
        end as replacement_ppg,

        -- Elite threshold (top 5 average)
        (
            select avg(points_per_game)
            from current_performance as cp
            where cp.position = crl.position and cp.current_rank_position <= 5
        ) as elite_avg_ppg

    from (select distinct position from current_performance) as crl
),

-- Calculate actual realized value for each pick
realized_value as (
    select
        dp.pick_no,
        dp.player_id,
        dp.player_name,
        dp.position,
        dp.round,
        dp.draft_slot,
        dp.roster_id,  -- For manager join

        -- Actual performance
        cp.points_per_game,
        cp.total_points,
        cp.games_played,
        cp.current_rank_position,
        cp.current_rank_overall,

        -- Replacement level comparison (current)
        crl.replacement_ppg,
        crl.elite_avg_ppg,

        -- REALIZED Value Over Replacement (based on actual performance)
        case
            when
                cp.points_per_game is not null
                and crl.replacement_ppg is not null
                then
                    (cp.points_per_game - crl.replacement_ppg) * cp.games_played
            else 0
        end as realized_vor,

        -- Points above/below replacement
        case
            when
                cp.points_per_game is not null
                and crl.replacement_ppg is not null
                then cp.total_points - (crl.replacement_ppg * cp.games_played)
        end as total_points_above_replacement,

        -- Is this player actually startable?
        case
            when
                cp.points_per_game is not null
                and crl.replacement_ppg is not null
                then cp.points_per_game > crl.replacement_ppg
            else false
        end as actually_startable,

        -- Is this player actually elite?
        case
            when cp.current_rank_position is not null
                then cp.current_rank_position <= 5
            else false
        end as actually_elite,

        -- Draft position context
        case
            when dp.round <= 3 then 'EARLY (Elite Expected)'
            when dp.round between 4 and 7 then 'MID (Starter Expected)'
            when dp.round between 8 and 10 then 'LATE (Depth Expected)'
            else 'VERY_LATE (Flyer)'
        end as draft_tier,

        -- Expected vs Actual performance
        case
            when dp.round <= 3 and cp.current_rank_position is not null
                then dp.pick_no - cp.current_rank_overall
        end as early_round_value_delta

    from draft_picks as dp
    left join current_performance as cp on dp.player_id = cp.player_id
    left join current_replacement_levels as crl on dp.position = crl.position
),

-- Calculate value tiers and grades
with_value_grades as (
    select
        rv.*,

        -- Value Tier (based on realized VOR)
        case
            when rv.realized_vor >= 100 then 'LEAGUE_WINNER'
            when rv.realized_vor >= 50 then 'EXCELLENT_VALUE'
            when rv.realized_vor >= 20 then 'GOOD_VALUE'
            when rv.realized_vor >= 0 then 'REPLACEMENT_VALUE'
            when rv.realized_vor >= -20 then 'BELOW_REPLACEMENT'
            else 'NEGATIVE_VALUE'
        end as value_tier,

        -- Outcome Grade (hindsight-based)
        case
            -- Inactive/Injured
            when rv.games_played = 0 or rv.games_played is null
                then 'F (INACTIVE/INJURED)'

            -- EARLY ROUNDS (1-3): Need elite performance
            when rv.round <= 3
                then
                    case
                        when rv.actually_elite and rv.realized_vor >= 80
                            then 'A+ (Elite as Expected)'
                        when rv.actually_elite
                            then 'A (Elite but Missed Games)'
                        when rv.actually_startable and rv.realized_vor >= 40
                            then 'B (Solid Starter)'
                        when rv.actually_startable
                            then 'C (Startable but Disappointing)'
                        when rv.current_rank_position <= 24
                            then 'D (Bench Player - Major Bust)'
                        else 'F (Complete Bust)'
                    end

            -- MID ROUNDS (4-7): Starter quality expected
            when rv.round between 4 and 7
                then
                    case
                        when rv.actually_elite and rv.realized_vor >= 60
                            then 'A+ (Massive Steal)'
                        when rv.actually_elite
                            then 'A (Elite Value)'
                        when rv.actually_startable and rv.realized_vor >= 30
                            then 'B+ (Great Value)'
                        when rv.actually_startable and rv.realized_vor >= 15
                            then 'B (Good Value)'
                        when rv.actually_startable
                            then 'C+ (Met Expectations)'
                        when rv.current_rank_position <= 36
                            then 'C (Bench Depth)'
                        else 'D (Wasted Pick)'
                    end

            -- LATE ROUNDS (8+): Any value is good
            when rv.round >= 8
                then
                    case
                        when rv.actually_elite
                            then 'A+ (Lightning in a Bottle)'
                        when rv.actually_startable and rv.realized_vor >= 20
                            then 'A (Excellent Late Value)'
                        when rv.actually_startable
                            then 'B+ (Found a Starter)'
                        when rv.current_rank_position <= 48
                            then 'B (Useful Depth)'
                        else 'C (Did Not Pan Out)'
                    end

            else 'N/A'
        end as outcome_grade,

        -- Value per draft position (VOR / pick_no)
        -- Earlier picks should deliver more value
        case
            when rv.pick_no > 0
                then round(rv.realized_vor / rv.pick_no, 2)
            else 0
        end as value_per_draft_capital,

        -- Games played rate
        round(cast(rv.games_played as decimal) / 17 * 100, 1)
            as games_played_pct

    from realized_value as rv
),

-- Add best/worst pick context by round
with_round_context as (
    select
        vg.*,

        -- Best pick in this round
        max(vg.realized_vor) over (partition by vg.round) as round_best_vor,

        -- Worst pick in this round
        min(vg.realized_vor) over (partition by vg.round) as round_worst_vor,

        -- Average VOR for this round
        avg(vg.realized_vor) over (partition by vg.round) as round_avg_vor,

        -- Rank within round by VOR
        row_number()
            over (partition by vg.round order by vg.realized_vor desc)
            as rank_within_round,

        -- Best pick in this position
        max(vg.realized_vor)
            over (partition by vg.position)
            as position_best_vor,

        -- Rank within position by VOR
        row_number()
            over (partition by vg.position order by vg.realized_vor desc)
            as rank_within_position

    from with_value_grades as vg
),

-- Add manager context
final as (
    select
        rc.*,
        r.owner_id,
        u.display_name as manager_name

    from with_round_context as rc
    left join {{ ref('stg_rosters') }} as r
        on rc.roster_id = r.roster_id
    left join {{ ref('stg_users') }} as u
        on r.owner_id = u.user_id
)

select * from final
order by realized_vor desc
