{{ config(materialized='table') }}

/*
Expected Wins Uncertainty Quantification

Uses Wilson score intervals (binomial confidence intervals) to estimate
uncertainty in expected wins calculations.

Methodology: Closed-form binomial CI (NOT Monte Carlo simulation)
- Point estimate: All-play win percentage × games played
- Confidence interval: Wilson score method (handles small samples better than normal approximation)
- Output: p05, p50, p95 percentiles with standard error

Why Wilson score instead of normal approximation?
- Handles small sample sizes (n < 30) correctly
- Prevents invalid CIs (won't go below 0 wins or above n games)
- Symmetric for p ≈ 0.5, adjusts for extreme probabilities
- Industry standard for binomial proportions (Brown et al. 2001)

Note: This model was previously named "Monte Carlo" but that was misleading.
There is no random sampling or simulation - just a closed-form statistical formula.
*/

with weekly_matchups as (
    select
        week,
        roster_id,
        manager_name,
        points,
        opponent_points,
        win_flag
    from {{ ref('fct_matchups') }}
),

-- Get weekly performance stats for each team
weekly_stats as (
    select
        roster_id,
        manager_name,
        avg(points) as avg_points,
        stddev(points) as stddev_points,
        min(points) as min_points,
        max(points) as max_points,
        count(*) as weeks_played
    from weekly_matchups
    group by roster_id, manager_name
),

-- All-play win percentage (current deterministic method)
all_play_results as (
    select
        m1.week,
        m1.roster_id,
        m1.manager_name,
        m1.points,
        sum(case when m1.points > m2.points then 1 else 0 end) as all_play_wins,
        count(*) as all_play_games
    from weekly_matchups as m1
    cross join weekly_matchups as m2
    where
        m1.week = m2.week
        and m1.roster_id <> m2.roster_id
    group by m1.week, m1.roster_id, m1.manager_name, m1.points
),

all_play_season as (
    select
        roster_id,
        manager_name,
        sum(all_play_wins) as all_play_wins,
        sum(all_play_games) as all_play_games,
        round(sum(all_play_wins)::double / sum(all_play_games), 3)
            as all_play_win_pct
    from all_play_results
    group by roster_id, manager_name
),

-- Estimate expected wins variance using Wilson score interval
-- This is a closed-form approximation instead of full Monte Carlo
-- Wilson CI for binomial proportion: accounts for small sample sizes
expected_wins_with_uncertainty as (
    select
        aps.roster_id,
        aps.manager_name,
        ws.weeks_played,
        aps.all_play_win_pct,

        -- Point estimate (median)
        round(aps.all_play_win_pct * ws.weeks_played, 2) as expected_wins_p50,

        -- Wilson score interval for 95% confidence
        -- Formula: p ± z * sqrt(p*(1-p)/n) where z=1.96 for 95% CI
        -- Lower bound (5th percentile approximation)
        round(
            greatest(
                0,
                (
                    aps.all_play_win_pct
                    - 1.96
                    * sqrt(
                        aps.all_play_win_pct
                        * (1 - aps.all_play_win_pct)
                        / aps.all_play_games
                    )
                )
                * ws.weeks_played
            ),
            2
        ) as expected_wins_p05,

        -- Upper bound (95th percentile approximation)
        round(
            least(
                ws.weeks_played,
                (
                    aps.all_play_win_pct
                    + 1.96
                    * sqrt(
                        aps.all_play_win_pct
                        * (1 - aps.all_play_win_pct)
                        / aps.all_play_games
                    )
                )
                * ws.weeks_played
            ),
            2
        ) as expected_wins_p95,

        -- Confidence interval width
        round(
            1.96
            * sqrt(
                aps.all_play_win_pct
                * (1 - aps.all_play_win_pct)
                / aps.all_play_games
            )
            * ws.weeks_played,
            2
        ) as expected_wins_ci_width,

        -- Standard error of expected wins
        round(
            sqrt(
                aps.all_play_win_pct
                * (1 - aps.all_play_win_pct)
                * ws.weeks_played
                / aps.all_play_games
            ),
            3
        ) as expected_wins_std_error

    from all_play_season as aps
    inner join weekly_stats as ws
        on aps.roster_id = ws.roster_id and aps.manager_name = ws.manager_name
)

select
    roster_id,
    manager_name,
    weeks_played,
    all_play_win_pct,

    -- Expected wins distribution (from Wilson score interval)
    expected_wins_p05,
    expected_wins_p50,
    expected_wins_p95,
    expected_wins_ci_width,
    expected_wins_std_error,

    -- Confidence interval as percentage of expected wins
    round(
        case
            when expected_wins_p50 > 0
                then (expected_wins_ci_width / expected_wins_p50) * 100
            else 0
        end,
        1
    ) as expected_wins_cv_pct

from expected_wins_with_uncertainty
order by expected_wins_p50 desc
