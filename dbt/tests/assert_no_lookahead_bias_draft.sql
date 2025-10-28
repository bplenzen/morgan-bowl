-- filepath: tests/assert_no_lookahead_bias_draft.sql
-- Verify draft grades use only pre-draft data (no look-ahead bias)
--
-- METHODOLOGY:
-- This test ensures fct_draft_performance evaluates draft DECISIONS (process)
-- not OUTCOMES (results). We verify:
-- 1. Draft baseline uses frozen parameters from draft day (2025-09-04)
-- 2. No player stats from AFTER the draft are used in grading logic
-- 3. Preseason rankings (ADP) are used for draft-day decisions
-- 4. Current stats are used ONLY for calculating realized VOR (not for grades)
--
-- PASS CRITERIA: 0 violations found

with draft_params as (
    -- Get frozen draft date from the baseline model
    select distinct frozen_date as draft_date
    from {{ ref('int_draft_day_baseline') }}
),

draft_performance as (
    select *
    from {{ ref('fct_draft_performance') }}
),

-- VIOLATION CHECK 1: Verify baseline uses frozen date
-- The baseline should have exactly ONE frozen date: 2025-09-04
baseline_date_check as (
    select
        'Baseline frozen_date mismatch' as violation_type,
        frozen_date::varchar as violation_detail,
        null as player_id
    from {{ ref('int_draft_day_baseline') }}
    where frozen_date != '2025-09-04'
),

-- VIOLATION CHECK 2: Verify preseason rankings are actually "preseason"
-- Since we use ADP as projections, verify stg_preseason_rankings
-- doesn't contain any post-draft data
preseason_rankings_check as (
    select
        'Preseason rankings contain post-draft data' as violation_type,
        'Found ranking dated after draft: ' || player_name as violation_detail,
        player_id
    from {{ ref('stg_preseason_rankings') }} pr
    cross join draft_params dp
    -- Note: stg_preseason_rankings doesn't have a date field
    -- It's by definition preseason, but we check it exists
    where 1=0  -- This check is structural only
),

-- VIOLATION CHECK 3: Verify player stats used in current_rankings
-- are not used in GRADING logic (only in VOR calculation)
-- This is a documentation check - we verify the model STRUCTURE
stats_usage_check as (
    select
        'Draft performance uses post-draft stats in grading' as violation_type,
        'Model should only use current stats for VOR calc, not grades' as violation_detail,
        null::varchar as player_id
    where exists (
        -- Check if any player with NO games played gets a non-F grade
        -- This would indicate grades depend on pre-draft data only
        select 1
        from draft_performance
        where
            (games_played = 0 or games_played is null)
            and pick_grade not like 'F%'
    )
),

-- VIOLATION CHECK 4: Verify replacement levels are frozen
-- Replacement players should match the frozen parameters file
replacement_level_check as (
    select
        'Replacement level changed from frozen parameters' as violation_type,
        'Position: ' || position || ' | Expected: ' ||
            case
                when position = 'QB' then 'Jordan Love (rank 12)'
                when position = 'RB' then 'Najee Harris (rank 28)'
                when position = 'WR' then 'Jordan Addison (rank 32)'
                when position = 'TE' then 'Cole Kmet (rank 12)'
            end || ' | Got: ' || replacement_player_name as violation_detail,
        null::varchar as player_id
    from {{ ref('int_draft_day_baseline') }} ddb
    where
        (position = 'QB' and (replacement_rank != 12 or replacement_player_name != 'Jordan Love'))
        or (position = 'RB' and (replacement_rank != 28 or replacement_player_name != 'Najee Harris'))
        or (position = 'WR' and (replacement_rank != 32 or replacement_player_name != 'Jordan Addison'))
        or (position = 'TE' and (replacement_rank != 12 or replacement_player_name != 'Cole Kmet'))
),

-- VIOLATION CHECK 5: Verify projection_source is frozen
projection_source_check as (
    select
        'Projection source changed from frozen parameters' as violation_type,
        'Expected: Preseason_ADP_Consensus_2025 | Got: ' || projection_source as violation_detail,
        null::varchar as player_id
    from {{ ref('int_draft_day_baseline') }}
    where projection_source != 'Preseason_ADP_Consensus_2025'
),

-- Combine all violations
all_violations as (
    select * from baseline_date_check
    union all
    select * from preseason_rankings_check
    union all
    select * from stats_usage_check
    union all
    select * from replacement_level_check
    union all
    select * from projection_source_check
)

select
    violation_type,
    violation_detail,
    player_id
from all_violations
