{{ config(materialized='table') }}

/*
Playoff Probability Calculator - Monte Carlo Simulation (SQL approximation)

Since we can't do true random simulation in SQL, we use:
1. Team scoring distributions (mean, stddev from actual games)
2. Opponent strength (remaining schedule)
3. Binomial approximation for win probability
4. Aggregate to playoff probability

This is a simplified version. True Monte Carlo would be in Python.
*/

with league_config as (
    select
        total_rosters,
        playoff_teams,
        playoff_week_start,
        -- Calculate regular season weeks
        playoff_week_start - 1 as regular_season_weeks
    from {{ ref('stg_league') }}
),

current_standings as (
    select * from {{ ref('fct_standings') }}
),

weekly_stats as (
    select
        roster_id,
        manager_name,
        avg(points) as avg_points,
        stddev(points) as stddev_points,
        count(*) as weeks_played
    from {{ ref('fct_matchups') }}
    group by roster_id, manager_name
),

-- Estimate win probability for remaining games
-- Using normal approximation: P(win) = P(score > opponent_avg_score)
win_probability_estimate as (
    select
        cs.roster_id,
        cs.manager_name,
        cs.wins as current_wins,
        cs.losses as current_losses,
        ws.avg_points as team_avg,
        ws.stddev_points as team_stddev,

        -- League average (opponent strength proxy)
        lc.playoff_teams,
        (select avg(avg_points) from weekly_stats) as league_avg,

        -- Calculate games remaining directly
        (select avg(stddev_points) from weekly_stats) as league_stddev,

        -- Include playoff_teams for later use
        lc.regular_season_weeks - cs.wins - cs.losses as games_remaining,

        -- Win probability estimate (assuming normal distributions)
        -- P(X > Y) where X ~ N(mu_team, sigma_team), Y ~ N(mu_league, sigma_league)
        -- = P(X - Y > 0) where (X-Y) ~ N(mu_team - mu_league, sqrt(sigma_team^2 + sigma_league^2))
        -- = 1 - CDF( (0 - (mu_team - mu_league)) / sqrt(sigma_team^2 + sigma_league^2) )
        -- SQL doesn't have normal CDF, so approximate with logistic: 1 / (1 + exp(-z))

        1.0 / (1.0 + exp(
            -(ws.avg_points - (select avg(avg_points) from weekly_stats))
            / sqrt(power(ws.stddev_points, 2) + power((select avg(stddev_points) from weekly_stats), 2))
        )) as win_prob_per_game

    from current_standings as cs
    inner join weekly_stats as ws on cs.roster_id = ws.roster_id
    cross join league_config as lc
),

-- Expected final record using binomial distribution
expected_final_record as (
    select
        wpe.*,

        -- Expected wins = current wins + (games_remaining × win_prob)
        wpe.current_wins
        + (wpe.games_remaining * wpe.win_prob_per_game) as expected_final_wins,

        -- Standard deviation of remaining wins (binomial: sqrt(n*p*(1-p)))
        sqrt(
            wpe.games_remaining
            * wpe.win_prob_per_game
            * (1 - wpe.win_prob_per_game)
        ) as final_wins_stddev,

        -- Confidence intervals (±1.96 stddev for 95% CI)
        wpe.current_wins + (wpe.games_remaining * wpe.win_prob_per_game)
        - 1.96 * sqrt(wpe.games_remaining * wpe.win_prob_per_game * (1 - wpe.win_prob_per_game))
            as expected_wins_lower,

        wpe.current_wins + (wpe.games_remaining * wpe.win_prob_per_game)
        + 1.96 * sqrt(wpe.games_remaining * wpe.win_prob_per_game * (1 - wpe.win_prob_per_game))
            as expected_wins_upper

    from win_probability_estimate as wpe
),

-- Approximate playoff probability
-- (This is a rough approximation; true simulation would be better)
ranked_expected_record as (
    select
        efr.*,
        row_number() over (order by efr.expected_final_wins desc) as rank
    from expected_final_record as efr
),

playoff_cutoff_estimate as (
    select avg(rer.expected_final_wins) as cutoff_wins
    from ranked_expected_record as rer
    cross join league_config as lc
    -- Get the team right on the playoff bubble (last playoff team)
    where rer.rank = lc.playoff_teams
),

-- When regular season is complete (games_remaining = 0), rank by actual record
with_actual_standings as (
    select
        efr.*,
        cs.points_for,
        -- Rank by wins then points_for (standard tiebreaker)
        row_number() over (order by efr.current_wins desc, cs.points_for desc) as final_rank
    from expected_final_record as efr
    inner join current_standings as cs on efr.roster_id = cs.roster_id
),

final as (
    select
        was.roster_id,
        was.manager_name,
        was.current_wins,
        was.current_losses,
        was.games_remaining,
        pce.cutoff_wins as playoff_cutoff_estimate,
        round(was.win_prob_per_game, 3) as win_prob_remaining_games,
        round(was.expected_final_wins, 1) as expected_final_wins,
        round(was.expected_wins_lower, 1) as expected_wins_lower,

        round(was.expected_wins_upper, 1) as expected_wins_upper,

        -- Playoff probability
        -- If regular season is complete (games_remaining = 0), use actual standings
        -- Otherwise use probabilistic calculation
        round(
            case
                when was.games_remaining = 0 then
                    case
                        when was.final_rank <= was.playoff_teams then 100.0
                        else 0.0
                    end
                else
                    1.0 / (1.0 + exp(
                        -(was.expected_final_wins - pce.cutoff_wins)
                        / greatest(was.final_wins_stddev, 0.5)
                    )) * 100
            end,
            1
        ) as playoff_probability_pct,

        case
            when was.games_remaining = 0 then
                case
                    when was.final_rank <= was.playoff_teams then 'CLINCHED'
                    else 'ELIMINATED'
                end
            when
                was.expected_final_wins
                > pce.cutoff_wins + was.final_wins_stddev
                then 'SAFE'
            when was.expected_final_wins > pce.cutoff_wins
                then 'LIKELY'
            when
                was.expected_final_wins
                > pce.cutoff_wins - was.final_wins_stddev
                then 'BUBBLE'
            else 'LONGSHOT'
        end as playoff_status

    from with_actual_standings as was
    cross join playoff_cutoff_estimate as pce
)

select * from final
order by playoff_probability_pct desc
