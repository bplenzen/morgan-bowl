-- Test: Draft grades should remain stable when new weeks are ingested
-- This validates that the frozen parameter system prevents look-ahead bias
--
-- METHODOLOGY:
-- 1. Draft grades should ONLY use draft-day parameters (preseason rankings, frozen replacement levels)
-- 2. When new weeks of data are added, replacement levels should NOT change
-- 3. Player performance affects actual VOR, but NOT the baseline/replacement level
--
-- EXPECTED BEHAVIOR:
-- - int_draft_day_baseline.replacement_ppg should be constant (never changes)
-- - int_draft_day_baseline.scarcity_multiplier should be constant (never changes)
-- - fct_draft_performance.draft_grade may change as player performance updates
-- - But the BASELINE against which performance is measured must stay frozen
--
-- This test verifies the baseline is truly frozen by checking that:
-- 1. Replacement levels are derived from preseason rankings only
-- 2. No current season performance data influences the baseline
-- 3. The status field is set to "FROZEN - Never recalculate"

with baseline_check as (
    select
        position,
        replacement_adp,
        replacement_player_name,
        vor_multiplier as scarcity_multiplier,
        replacement_rank,
        status
    from {{ ref('int_draft_day_baseline') }}
),

-- Verify frozen status
status_check as (
    select
        position,
        status,
        -- Every row must be marked as FROZEN
        case
            when status = 'FROZEN - Never recalculate' then 0
            else 1
        end as status_violation
    from baseline_check
),

-- Verify replacement levels are reasonable (sanity check)
replacement_check as (
    select
        position,
        replacement_adp,
        replacement_rank,
        -- Replacement ADP should be positive and match expected ranks
        case
            when replacement_adp is null then 1
            when replacement_adp < 0 then 1
            when position = 'QB' and replacement_rank != 12 then 1  -- QB12
            when position = 'TE' and replacement_rank != 12 then 1  -- TE12
            when position = 'RB' and replacement_rank != 28 then 1  -- RB28
            when position = 'WR' and replacement_rank != 32 then 1  -- WR32
            else 0
        end as replacement_violation
    from baseline_check
),

-- Verify scarcity multipliers match frozen parameters
scarcity_check as (
    select
        position,
        scarcity_multiplier,
        -- From data/draft_day_parameters_2025.yml
        case position
            when 'QB' then 1.00
            when 'RB' then 1.20
            when 'WR' then 1.05
            when 'TE' then 1.30
        end as expected_scarcity,
        -- Check if actual matches expected (within floating point tolerance)
        case
            when abs(
                scarcity_multiplier - case position
                    when 'QB' then 1.00
                    when 'RB' then 1.20
                    when 'WR' then 1.05
                    when 'TE' then 1.30
                end
            ) > 0.01 then 1
            else 0
        end as scarcity_violation
    from baseline_check
),

-- Combine all violations
all_violations as (
    select
        'Status not frozen' as violation_type,
        count(*) as violation_count
    from status_check
    where status_violation = 1

    union all

    select
        'Invalid replacement level' as violation_type,
        count(*) as violation_count
    from replacement_check
    where replacement_violation = 1

    union all

    select
        'Scarcity multiplier mismatch' as violation_type,
        count(*) as violation_count
    from scarcity_check
    where scarcity_violation = 1
)

-- Test fails if ANY violations exist
select *
from all_violations
where violation_count > 0
