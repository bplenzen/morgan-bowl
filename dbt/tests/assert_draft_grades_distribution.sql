/*
Data Quality Test: Draft Grades Distribution Is Realistic
Ensures grades follow a reasonable distribution (not all A+ or all F).
No single grade should dominate (>50% of all picks).
This catches issues with grading logic or thresholds.
*/

with grade_distribution as (
    select
        pick_grade,
        count(*) as pick_count,
        round(count(*) * 100.0 / sum(count(*)) over (), 1) as pct_of_total
    from {{ ref('fct_draft_performance') }}
    where pick_grade != 'INACTIVE'  -- Exclude inactive players
    group by pick_grade
),

problematic_grades as (
    select
        pick_grade,
        pick_count,
        pct_of_total,
        'Grade represents > 50% of all picks' as issue
    from grade_distribution
    where pct_of_total > 50.0
)

select * from problematic_grades
