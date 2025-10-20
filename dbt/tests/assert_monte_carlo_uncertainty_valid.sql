-- Test: Monte Carlo expected wins uncertainty intervals are reasonable
-- Validates that:
-- 1. CI width is proportional to uncertainty (more games = tighter CI)
-- 2. p05 < p50 < p95 (proper ordering)
-- 3. Confidence intervals don't exceed physically possible bounds (0 to total weeks)
-- 4. Standard errors are reasonable (< 1.5 wins)

with uncertainty_checks as (
    select
        manager_name,
        weeks_played,
        expected_wins_p05,
        expected_wins_p50,
        expected_wins_p95,
        expected_wins_ci_width,
        expected_wins_std_error,

        -- Check 1: Proper ordering
        case
            when expected_wins_p05 > expected_wins_p50 then 'p05 > p50'
            when expected_wins_p50 > expected_wins_p95 then 'p50 > p95'
        end as ordering_violation,

        -- Check 2: Physical bounds
        case
            when expected_wins_p05 < 0 then 'p05 < 0'
            when expected_wins_p95 > weeks_played then 'p95 > weeks_played'
        end as bounds_violation,

        -- Check 3: Reasonable CI width (should be < 2 wins for 6-week season)
        case
            when expected_wins_ci_width > 2.0 then 'ci_width too large'
        end as ci_width_violation,

        -- Check 4: Reasonable standard error (should be < 1.5 wins)
        case
            when expected_wins_std_error > 1.5 then 'std_error too large'
        end as std_error_violation

    from {{ ref('int_monte_carlo_expected_wins') }}
)

-- Test FAILS if any violations detected
select
    manager_name,
    expected_wins_p05,
    expected_wins_p50,
    expected_wins_p95,
    expected_wins_ci_width,
    expected_wins_std_error,
    coalesce(ordering_violation, 'OK') as ordering_check,
    coalesce(bounds_violation, 'OK') as bounds_check,
    coalesce(ci_width_violation, 'OK') as ci_width_check,
    coalesce(std_error_violation, 'OK') as std_error_check,
    'Uncertainty intervals must be properly ordered and within reasonable bounds' as failure_reason
from uncertainty_checks
where
    ordering_violation is not null
    or bounds_violation is not null
    or ci_width_violation is not null
    or std_error_violation is not null
