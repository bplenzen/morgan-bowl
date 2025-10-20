-- Test: League-wide luck should sum to zero (within floating-point tolerance)
-- Rationale: Wins over expected is a zero-sum metric - one team's good luck
-- is another team's bad luck. Total league deviation should be negligible.
--
-- Tolerance: 1e-6 (0.000001 wins)
-- This accounts for floating-point rounding in DuckDB calculations

with league_luck_totals as (
    select
        sum(wins_over_expected) as total_luck,
        sum(abs(wins_over_expected)) as total_absolute_luck,
        count(*) as teams_count,
        round(avg(wins_over_expected), 6) as avg_luck_per_team
    from {{ ref('fct_advanced_luck') }}
)

-- Test FAILS if total_luck deviates from zero beyond tolerance
-- Returns rows only when violation detected
select
    total_luck,
    total_absolute_luck,
    teams_count,
    avg_luck_per_team,
    'League-wide luck must sum to 0 (tolerance: 1e-6)' as failure_reason
from league_luck_totals
where abs(total_luck) > 0.000001
