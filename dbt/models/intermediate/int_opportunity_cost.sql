{{ config(materialized='table') }}

/*
Opportunity Cost Analysis - Draft Day Focused
For each draft pick, identifies whether you "reached" based on PRESEASON rankings.
Compares your pick to the best player still available at that position based on ADP.

This is DRAFT DAY analysis, not hindsight. If you draft someone at pick 50 who was
ranked 80th in preseason, but someone ranked 40th was still available, you reached.

Key Metrics:
- Best available ADP at position (what was on the board)
- Reach = Your pick's ADP - Best available ADP (negative = reach, positive = value)
- Hindsight comparison available but not primary metric

Example: Draft WR ranked 60th at pick 30, but WR ranked 40th still on board = -20 reach
*/

with draft_picks as (
    select
        player_id,
        player_name,
        position,
        pick_no,
        round,
        draft_slot
    from {{ ref('stg_draft_picks') }}
),

preseason_rankings as (
    select
        player_id,
        player_name,
        position,
        preseason_adp,
        preseason_rank_overall,
        preseason_rank_position
    from {{ ref('stg_preseason_rankings') }}
),

current_performance as (
    select
        player_id,
        points_per_game,
        total_points,
        current_rank_position,
        games_played
    from {{ ref('int_current_player_rankings') }}
),

-- Calculate replacement levels based on FLEX simulation
-- QB12, RB28, WR32, TE12 (4 RB + 8 WR in FLEX based on preseason ADP)
replacement_levels as (
    select
        position,
        case
            when position = 'QB'
                then (
                    select points_per_game
                    from {{ ref('int_current_player_rankings') }}
                    where position = 'QB' and current_rank_position = 12
                )
            when position = 'TE'
                then (
                    select points_per_game
                    from {{ ref('int_current_player_rankings') }}
                    where position = 'TE' and current_rank_position = 12
                )
            when position = 'RB'
                then (
                    select points_per_game
                    from {{ ref('int_current_player_rankings') }}
                    where position = 'RB' and current_rank_position = 28
                )
            when position = 'WR' then (
                select points_per_game
                from {{ ref('int_current_player_rankings') }}
                where position = 'WR' and current_rank_position = 32
            )
        end as replacement_ppg
    from
        (select distinct position from {{ ref('int_current_player_rankings') }}
        ) as cr
),

-- Combine draft picks with their preseason rankings and current performance
picks_with_rankings as (
    select
        dp.pick_no,
        dp.player_id,
        dp.player_name,
        dp.position,
        dp.round,
        pr.preseason_adp,
        pr.preseason_rank_position,
        cp.points_per_game,
        cp.current_rank_position,
        cp.games_played,
        -- Calculate actual VOR for hindsight comparison
        case
            when
                cp.points_per_game is not null
                and rl.replacement_ppg is not null
                then
                    (cp.points_per_game - rl.replacement_ppg) * cp.games_played
        end as actual_vor
    from draft_picks as dp
    left join preseason_rankings as pr on dp.player_id = pr.player_id
    left join current_performance as cp on dp.player_id = cp.player_id
    left join replacement_levels as rl on dp.position = rl.position
    where dp.position not in ('DEF', 'K')  -- Focus on skill positions
),

-- For each pick, find the best player at same position still available based on PRESEASON ADP
opportunity_analysis as (
    select
        p1.pick_no,
        p1.player_id,
        p1.player_name,
        p1.position,
        p1.round,
        p1.preseason_adp,
        p1.preseason_rank_position,
        p1.actual_vor,
        p1.points_per_game as actual_ppg,
        p1.current_rank_position as actual_rank,

        -- Best player at same position drafted AFTER this pick (by preseason ADP)
        (
            select p2.player_id
            from picks_with_rankings as p2
            where
                p2.position = p1.position
                and p2.pick_no > p1.pick_no
                and p2.preseason_adp is not null
            -- Lower ADP = better preseason ranking
            order by p2.preseason_adp asc
            limit 1
        ) as best_available_player_id,

        (
            select p2.player_name
            from picks_with_rankings as p2
            where
                p2.position = p1.position
                and p2.pick_no > p1.pick_no
                and p2.preseason_adp is not null
            order by p2.preseason_adp asc
            limit 1
        ) as best_available_player_name,

        (
            select p2.pick_no
            from picks_with_rankings as p2
            where
                p2.position = p1.position
                and p2.pick_no > p1.pick_no
                and p2.preseason_adp is not null
            order by p2.preseason_adp asc
            limit 1
        ) as best_available_pick_no,

        (
            select p2.preseason_adp
            from picks_with_rankings as p2
            where
                p2.position = p1.position
                and p2.pick_no > p1.pick_no
                and p2.preseason_adp is not null
            order by p2.preseason_adp asc
            limit 1
        ) as best_available_adp,

        (
            select p2.preseason_rank_position
            from picks_with_rankings as p2
            where
                p2.position = p1.position
                and p2.pick_no > p1.pick_no
                and p2.preseason_adp is not null
            order by p2.preseason_adp asc
            limit 1
        ) as best_available_preseason_rank,

        -- Also track hindsight best (actual VOR)
        (
            select p2.player_name
            from picks_with_rankings as p2
            where
                p2.position = p1.position
                and p2.pick_no > p1.pick_no
                and p2.actual_vor is not null
            order by p2.actual_vor desc
            limit 1
        ) as hindsight_best_player,

        (
            select p2.actual_vor
            from picks_with_rankings as p2
            where
                p2.position = p1.position
                and p2.pick_no > p1.pick_no
                and p2.actual_vor is not null
            order by p2.actual_vor desc
            limit 1
        ) as hindsight_best_vor

    from picks_with_rankings as p1
),

final as (
    select
        *,

        -- DRAFT DAY Opportunity Cost (negative = reach, positive = value pick)
        -- If you draft someone ranked 60th but someone ranked 40th was available, that's -20
        case
            when best_available_adp is not null and preseason_adp is not null
                then
                    best_available_adp - preseason_adp
        end as draft_day_opportunity_cost,

        -- How many picks later was the better-ranked player available?
        case
            when best_available_pick_no is not null
                then
                    best_available_pick_no - pick_no
        end as picks_until_better_option,

        -- Hindsight opportunity cost (for comparison)
        case
            when hindsight_best_vor is not null and actual_vor is not null
                then
                    hindsight_best_vor - actual_vor
        end as hindsight_opportunity_cost,

        -- Draft day opportunity cost tier (based on ADP differential)
        case
            when best_available_adp is null then 'NO_BETTER_OPTION'
            -- Got best or better available
            when best_available_adp - preseason_adp >= 0 then 'OPTIMAL_PICK'
            when best_available_adp - preseason_adp >= -10 then 'MINOR_REACH'
            when best_available_adp - preseason_adp >= -25 then 'MODERATE_REACH'
            when
                best_available_adp - preseason_adp >= -50
                then 'SIGNIFICANT_REACH'
            else 'MAJOR_REACH'
        end as opportunity_cost_tier,

        -- Verdict based on draft day info
        case
            when
                best_available_adp is null
                then 'Best available at position (by ADP)'
            when best_available_adp - preseason_adp >= 10
                then
                    'Great value - drafted player ranked '
                    || cast(
                        round(preseason_adp - best_available_adp, 0) as varchar
                    )
                    || ' spots higher than best available'
            when best_available_adp - preseason_adp >= 0
                then
                    'Optimal pick - best or near-best available by ADP'
            when best_available_adp - preseason_adp >= -10
                then
                    'Slight reach - better option available but defensible'
            when best_available_adp - preseason_adp >= -25
                then
                    'Moderate reach - ' || best_available_player_name
                    || ' (ADP ' || cast(round(best_available_adp, 0) as varchar)
                    || ') drafted '
                    || cast(best_available_pick_no - pick_no as varchar)
                    || ' picks later'
            when best_available_adp - preseason_adp >= -50
                then
                    'Significant reach - missed ' || best_available_player_name
                    || ' ranked '
                    || cast(
                        round(preseason_adp - best_available_adp, 0) as varchar
                    )
                    || ' spots higher'
            else
                'Major reach - ' || best_available_player_name
                || ' (ranked ' || cast(best_available_preseason_rank as varchar)
                || 'th at position) was still available'
        end as opportunity_verdict

    from opportunity_analysis
)

select * from final
order by draft_day_opportunity_cost asc nulls last
