-- ============================================================================
-- DRAFT ANALYSIS SAMPLE QUERIES
-- Showcase advanced features of the A+ research-grade draft analysis system
-- ============================================================================

-- ============================================================================
-- QUERY 1: Top Performers by Risk-Adjusted Scarcity VOR
-- Shows players who delivered the most value accounting for risk and scarcity
-- ============================================================================

SELECT
    player_name,
    position,
    round,
    pick_no,
    manager_name,

    -- Performance metrics
    points_per_game,
    games_played,
    current_rank_position,

    -- VOR progression
    value_over_replacement as raw_vor,
    scarcity_adjusted_vor,
    risk_adjusted_scarcity_vor,

    -- Risk factors
    risk_tier,
    consistency_tier,
    games_missed_pct,
    coefficient_of_variation as cv,

    -- Final grade
    pick_grade,
    grade_score,
    value_verdict

FROM {{ ref('fct_draft_performance') }}
WHERE risk_adjusted_scarcity_vor IS NOT NULL
ORDER BY risk_adjusted_scarcity_vor DESC
LIMIT 20;

-- ============================================================================
-- QUERY 2: Best Value Picks by Round
-- Identifies steals - players who massively outperformed draft position
-- ============================================================================

WITH round_stats AS (
    SELECT
        round,
        AVG(risk_adjusted_scarcity_vor) as avg_vor,
        STDDEV(risk_adjusted_scarcity_vor) as stddev_vor
    FROM {{ ref('fct_draft_performance') }}
    WHERE risk_adjusted_scarcity_vor IS NOT NULL
    GROUP BY round
)

SELECT
    dp.player_name,
    dp.position,
    dp.round,
    dp.pick_no,
    dp.manager_name,
    dp.preseason_adp,

    -- Value metrics
    dp.risk_adjusted_scarcity_vor,
    rs.avg_vor as round_avg_vor,
    dp.risk_adjusted_scarcity_vor - rs.avg_vor as vor_above_round_avg,

    -- How many standard deviations above round average?
    CASE
        WHEN rs.stddev_vor > 0 THEN
            ROUND((dp.risk_adjusted_scarcity_vor - rs.avg_vor) / rs.stddev_vor, 2)
        ELSE 0
    END as z_score,

    -- Opportunity cost
    dp.draft_day_opportunity_cost,
    dp.opportunity_verdict,

    -- Grade
    dp.pick_grade,
    dp.grade_score

FROM {{ ref('fct_draft_performance') }} dp
JOIN round_stats rs ON dp.round = rs.round
WHERE dp.risk_adjusted_scarcity_vor IS NOT NULL
  AND dp.risk_adjusted_scarcity_vor > rs.avg_vor  -- Above round average
ORDER BY
    dp.round ASC,
    (dp.risk_adjusted_scarcity_vor - rs.avg_vor) DESC
LIMIT 30;

-- ============================================================================
-- QUERY 3: Consistency Leaders (Weekly Reliability)
-- Players you can trust every week - low volatility, high availability
-- ============================================================================

SELECT
    player_name,
    position,
    round,
    pick_no,
    manager_name,

    -- Consistency metrics
    avg_weekly_points,
    coefficient_of_variation as cv,
    consistency_tier,

    -- Boom/Bust
    boom_rate_pct,
    bust_rate_pct,

    -- Floor/Ceiling
    floor_10th_percentile,
    ceiling_90th_percentile,
    ceiling_90th_percentile - floor_10th_percentile as range_width,

    -- Availability
    games_played,
    games_missed_pct,

    -- Risk tier
    risk_tier,

    -- Value created
    risk_adjusted_scarcity_vor,
    pick_grade

FROM {{ ref('fct_draft_performance') }}
WHERE games_played >= 5  -- Minimum sample size
  AND consistency_tier IN ('VERY_CONSISTENT', 'CONSISTENT')
ORDER BY coefficient_of_variation ASC
LIMIT 25;

-- ============================================================================
-- QUERY 4: Biggest Reaches (Draft Day Mistakes)
-- Players drafted way ahead of ADP who didn't deliver
-- ============================================================================

SELECT
    player_name,
    position,
    round,
    pick_no,
    manager_name,

    -- Draft day context
    preseason_adp,
    draft_day_opportunity_cost,
    opportunity_verdict,
    best_available_player_name,
    best_available_adp,

    -- How far did you reach?
    preseason_adp - pick_no as adp_vs_pick,

    -- Performance
    current_rank_position,
    points_per_game,
    value_over_replacement,
    risk_adjusted_scarcity_vor,

    -- Outcome
    pick_grade,
    grade_score,
    value_verdict

FROM {{ ref('fct_draft_performance') }}
WHERE draft_day_opportunity_cost < -10  -- Reached by 10+ spots
ORDER BY draft_day_opportunity_cost ASC  -- Most negative = biggest reach
LIMIT 20;

-- ============================================================================
-- QUERY 5: Late-Round Steals (Rounds 8+)
-- Hidden gems found in late rounds
-- ============================================================================

SELECT
    player_name,
    position,
    round,
    pick_no,
    manager_name,

    -- Draft context
    preseason_rank_position,
    current_rank_position,
    position_rank_differential,

    -- Performance
    points_per_game,
    games_played,

    -- Value metrics
    value_over_replacement,
    scarcity_adjusted_vor,
    risk_adjusted_scarcity_vor,

    -- Elite breakout?
    is_elite,
    is_startable,

    -- Grade
    pick_grade,
    grade_score,
    value_verdict

FROM {{ ref('fct_draft_performance') }}
WHERE round >= 8
  AND is_startable = TRUE
ORDER BY risk_adjusted_scarcity_vor DESC
LIMIT 20;

-- ============================================================================
-- QUERY 6: Positional Scarcity Impact
-- How much does scarcity multiplier change player rankings?
-- ============================================================================

WITH player_rankings AS (
    SELECT
        player_name,
        position,
        round,
        pick_no,

        -- VOR progression
        value_over_replacement,
        scarcity_adjusted_vor,
        risk_adjusted_scarcity_vor,

        -- Scarcity impact
        vor_multiplier,
        scarcity_adjusted_vor - value_over_replacement as scarcity_boost,

        -- Rankings
        ROW_NUMBER() OVER (ORDER BY value_over_replacement DESC) as rank_by_raw_vor,
        ROW_NUMBER() OVER (ORDER BY risk_adjusted_scarcity_vor DESC) as rank_by_final_vor,

        pick_grade

    FROM {{ ref('fct_draft_performance') }}
    WHERE value_over_replacement IS NOT NULL
)

SELECT
    player_name,
    position,
    round,
    pick_no,

    -- VOR values
    ROUND(value_over_replacement, 1) as raw_vor,
    ROUND(risk_adjusted_scarcity_vor, 1) as final_vor,
    ROUND(scarcity_boost, 1) as scarcity_boost,
    ROUND(vor_multiplier, 2) as multiplier,

    -- Rank movement
    rank_by_raw_vor,
    rank_by_final_vor,
    rank_by_raw_vor - rank_by_final_vor as rank_change,

    -- Interpretation
    CASE
        WHEN rank_by_raw_vor - rank_by_final_vor > 10 THEN 'JUMPED UP (scarcity helped)'
        WHEN rank_by_raw_vor - rank_by_final_vor < -10 THEN 'DROPPED DOWN (scarcity hurt)'
        ELSE 'MINIMAL CHANGE'
    END as scarcity_impact,

    pick_grade

FROM player_rankings
WHERE rank_by_raw_vor <= 50  -- Top 50 by raw VOR
ORDER BY ABS(rank_by_raw_vor - rank_by_final_vor) DESC
LIMIT 30;

-- ============================================================================
-- QUERY 7: Risk Penalty Impact
-- Players who lost the most value due to volatility/injuries
-- ============================================================================

SELECT
    player_name,
    position,
    round,
    pick_no,
    manager_name,

    -- Risk factors
    coefficient_of_variation as cv,
    consistency_tier,
    games_played,
    games_missed_pct,
    risk_tier,

    -- VOR before/after risk
    scarcity_adjusted_vor as vor_before_risk,
    risk_adjusted_scarcity_vor as vor_after_risk,
    vor_reduction_from_risk,
    ROUND(vor_reduction_from_risk * 100.0 / NULLIF(scarcity_adjusted_vor, 0), 1) as pct_reduction,

    -- Composite penalty breakdown
    composite_risk_penalty,

    -- Grade impact
    pick_grade,
    value_verdict

FROM {{ ref('fct_draft_performance') }}
WHERE vor_reduction_from_risk > 10  -- Lost 10+ VOR points to risk
ORDER BY vor_reduction_from_risk DESC
LIMIT 25;

-- ============================================================================
-- QUERY 8: Manager Draft Performance Summary
-- How did each manager draft overall?
-- ============================================================================

SELECT
    manager_name,

    -- Draft volume
    COUNT(*) as total_picks,
    COUNT(CASE WHEN is_elite THEN 1 END) as elite_picks,
    COUNT(CASE WHEN is_startable THEN 1 END) as startable_picks,

    -- Average value
    ROUND(AVG(risk_adjusted_scarcity_vor), 1) as avg_vor_per_pick,
    ROUND(SUM(risk_adjusted_scarcity_vor), 1) as total_vor,

    -- Grade distribution
    ROUND(AVG(grade_score), 1) as avg_grade_score,
    COUNT(CASE WHEN grade_score >= 90 THEN 1 END) as a_grades,
    COUNT(CASE WHEN grade_score >= 80 THEN 1 END) as b_grades,
    COUNT(CASE WHEN grade_score < 50 THEN 1 END) as failing_grades,

    -- Opportunity cost
    ROUND(AVG(draft_day_opportunity_cost), 1) as avg_opportunity_cost,
    COUNT(CASE WHEN opportunity_verdict LIKE '%REACH%' THEN 1 END) as reaches,
    COUNT(CASE WHEN opportunity_verdict LIKE '%VALUE%' THEN 1 END) as value_picks,

    -- Risk management
    COUNT(CASE WHEN risk_tier IN ('VERY_LOW_RISK', 'LOW_RISK') THEN 1 END) as low_risk_picks,
    COUNT(CASE WHEN risk_tier = 'HIGH_RISK' THEN 1 END) as high_risk_picks,

    -- Consistency
    COUNT(CASE WHEN consistency_tier IN ('VERY_CONSISTENT', 'CONSISTENT') THEN 1 END) as consistent_picks

FROM {{ ref('fct_draft_performance') }}
WHERE manager_name IS NOT NULL
GROUP BY manager_name
ORDER BY total_vor DESC;

-- ============================================================================
-- QUERY 9: Round-by-Round Hit Rate
-- What percentage of picks in each round delivered value?
-- ============================================================================

SELECT
    round,

    -- Volume
    COUNT(*) as total_picks,

    -- Success rates
    ROUND(100.0 * COUNT(CASE WHEN is_elite THEN 1 END) / COUNT(*), 1) as elite_rate_pct,
    ROUND(100.0 * COUNT(CASE WHEN is_startable THEN 1 END) / COUNT(*), 1) as startable_rate_pct,
    ROUND(100.0 * COUNT(CASE WHEN games_played = 0 THEN 1 END) / COUNT(*), 1) as bust_rate_pct,

    -- Average value
    ROUND(AVG(risk_adjusted_scarcity_vor), 1) as avg_vor,
    ROUND(AVG(grade_score), 1) as avg_grade,

    -- Best/worst in round
    MAX(player_name || ' (' || CAST(ROUND(risk_adjusted_scarcity_vor, 1) AS VARCHAR) || ' VOR)')
        FILTER (WHERE risk_adjusted_scarcity_vor = MAX(risk_adjusted_scarcity_vor) OVER (PARTITION BY round))
        as best_pick,

    -- Grade distribution
    COUNT(CASE WHEN grade_score >= 90 THEN 1 END) as a_tier,
    COUNT(CASE WHEN grade_score >= 70 AND grade_score < 90 THEN 1 END) as b_tier,
    COUNT(CASE WHEN grade_score >= 50 AND grade_score < 70 THEN 1 END) as c_tier,
    COUNT(CASE WHEN grade_score < 50 THEN 1 END) as d_f_tier

FROM {{ ref('fct_draft_performance') }}
GROUP BY round
ORDER BY round ASC;

-- ============================================================================
-- QUERY 10: Position-Specific VOR Leaders
-- Top performers at each position
-- ============================================================================

WITH position_ranks AS (
    SELECT
        player_name,
        position,
        round,
        pick_no,
        manager_name,

        -- Performance
        points_per_game,
        games_played,
        current_rank_position,

        -- VOR
        value_over_replacement,
        risk_adjusted_scarcity_vor,

        -- Risk/consistency
        risk_tier,
        consistency_tier,

        -- Grade
        pick_grade,
        grade_score,

        -- Rank within position
        ROW_NUMBER() OVER (PARTITION BY position ORDER BY risk_adjusted_scarcity_vor DESC) as pos_rank

    FROM {{ ref('fct_draft_performance') }}
    WHERE risk_adjusted_scarcity_vor IS NOT NULL
)

SELECT
    position,
    pos_rank,
    player_name,
    round,
    manager_name,
    points_per_game,
    games_played,
    current_rank_position,
    ROUND(risk_adjusted_scarcity_vor, 1) as final_vor,
    risk_tier,
    consistency_tier,
    pick_grade,
    grade_score

FROM position_ranks
WHERE pos_rank <= 10  -- Top 10 per position
ORDER BY position ASC, pos_rank ASC;
