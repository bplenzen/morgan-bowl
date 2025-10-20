-- Test that grade score confidence intervals are properly ordered
-- Lower bound ≤ Point estimate ≤ Upper bound

select
    player_id,
    player_name,
    pick_no,
    round,
    grade_score,
    grade_score_lower_bound,
    grade_score_upper_bound,
    grade_score_uncertainty
from {{ ref('fct_draft_performance') }}
where
    -- Only test players with games played
    games_played > 0
    and grade_score is not null
    and grade_score_lower_bound is not null
    and grade_score_upper_bound is not null
    -- Check for ordering violations
    and (
        grade_score_lower_bound > grade_score
        or grade_score > grade_score_upper_bound
    )
-- Should return 0 rows (no violations)
