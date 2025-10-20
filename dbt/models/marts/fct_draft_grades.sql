{{ config(materialized='table') }}

/*
Team-level draft report cards.
Aggregates draft performance to show which teams drafted best.
*/

with draft_performance as (
    select * from {{ ref('fct_draft_performance') }}
),

-- Aggregate by team
team_draft_summary as (
    select
        roster_id,
        manager_name,
        count(*) as total_picks,

        -- Grade distribution
        sum(case when pick_grade like 'A%' then 1 else 0 end) as a_grades,
        sum(case when pick_grade like 'B%' then 1 else 0 end) as b_grades,
        sum(case when pick_grade like 'C%' then 1 else 0 end) as c_grades,
        sum(case when pick_grade like 'D%' then 1 else 0 end) as d_grades,
        sum(case when pick_grade like 'F%' then 1 else 0 end) as f_grades,
        sum(
            case when pick_grade in ('UNRANKED', 'INACTIVE') then 1 else 0 end
        ) as ungraded,

        -- Performance metrics
        sum(total_points) as total_draft_points,
        avg(total_points) as avg_points_per_pick,
        sum(case when current_rank_overall <= 36 then 1 else 0 end)
            as top_36_picks,
        sum(case when current_rank_overall <= 60 then 1 else 0 end)
            as starter_quality_picks,

        -- Best/worst picks
        max(
            case
                when current_rank_overall is not null then total_points else 0
            end
        ) as best_pick_points,
        min(
            case
                when current_rank_overall is not null then total_points else 999
            end
        ) as worst_pick_points,

        -- Round performance
        sum(case when round <= 3 and pick_grade like 'A%' then 1 else 0 end)
            as early_round_hits,
        sum(
            case
                when round <= 3 and pick_grade in ('D%', 'F%') then 1 else 0
            end
        ) as early_round_misses,
        sum(case when round >= 10 and pick_grade like 'A%' then 1 else 0 end)
            as late_round_gems

    from draft_performance
    group by roster_id, manager_name
),

-- Calculate overall draft grade
graded as (
    select
        *,

        -- Calculate grade point average (A=4, B=3, C=2, D=1, F=0)
        case
            when (a_grades + b_grades + c_grades + d_grades + f_grades) > 0
                then
                    round(
                        (
                            (a_grades * 4.0)
                            + (b_grades * 3.0)
                            + (c_grades * 2.0)
                            + (d_grades * 1.0)
                        )
                        / (
                            a_grades + b_grades + c_grades + d_grades + f_grades
                        ),
                        2
                    )
        end as gpa,

        -- Overall draft grade
        case
            when
                (a_grades + b_grades + c_grades + d_grades + f_grades) = 0
                then 'INCOMPLETE'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 3.7
                then 'A+'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 3.3
                then 'A'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 3.0
                then 'A-'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 2.7
                then 'B+'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 2.3
                then 'B'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 2.0
                then 'B-'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 1.7
                then 'C+'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 1.3
                then 'C'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 1.0
                then 'C-'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 0.7
                then 'D+'
            when
                (
                    (a_grades * 4.0)
                    + (b_grades * 3.0)
                    + (c_grades * 2.0)
                    + (d_grades * 1.0)
                )
                / (a_grades + b_grades + c_grades + d_grades + f_grades) >= 0.3
                then 'D'
            else 'F'
        end as overall_draft_grade

    from team_draft_summary
)

select * from graded
order by gpa desc nulls last
