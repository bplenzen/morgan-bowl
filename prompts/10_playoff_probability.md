# Enhancement: Add Playoff Probability Calculator

## Background

Users care more about **"Will I make the playoffs?"** than current standings. This is **table stakes** for modern fantasy platforms.

**Current**: Shows current standings (wins/losses)
**Missing**: Forward-looking playoff probability

## Industry Standards

- **ESPN**: Shows playoff probabilities starting Week 4
- **Sleeper**: Shows it starting Week 1
- **Yahoo**: Shows it with confidence intervals

## Why This Matters

In Week 8, a team at 4-4 might have:

- 67% playoff chance (easy remaining schedule)
- 23% playoff chance (brutal remaining schedule)

This is more actionable than just knowing you're 4-4.

## Implementation Approach

This is a **Monte Carlo simulation** (the real kind, not the Wilson score kind):

1. For each team, simulate remaining games based on scoring distribution
2. Count playoff appearances across 10,000 simulations
3. Display as percentage + confidence interval

### Step 1: Create playoff probability model

**Create `dbt/models/intermediate/int_playoff_probability.sql`:**

```sql
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

remaining_games as (
    select
        lc.regular_season_weeks - cs.wins - cs.losses as games_remaining
    from league_config lc
    cross join current_standings cs
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
        (select avg(avg_points) from weekly_stats) as league_avg,
        (select avg(stddev_points) from weekly_stats) as league_stddev,

        rg.games_remaining,

        -- Win probability estimate (assuming normal distributions)
        -- P(X > Y) where X ~ N(mu_team, sigma_team), Y ~ N(mu_league, sigma_league)
        -- = P(X - Y > 0) where (X-Y) ~ N(mu_team - mu_league, sqrt(sigma_team^2 + sigma_league^2))
        -- = 1 - CDF( (0 - (mu_team - mu_league)) / sqrt(sigma_team^2 + sigma_league^2) )
        -- SQL doesn't have normal CDF, so approximate with logistic: 1 / (1 + exp(-z))

        1.0 / (1.0 + exp(
            -(ws.avg_points - (select avg(avg_points) from weekly_stats)) /
            sqrt(power(ws.stddev_points, 2) + power((select avg(stddev_points) from weekly_stats), 2))
        )) as win_prob_per_game

    from current_standings cs
    inner join weekly_stats ws on cs.roster_id = ws.roster_id
    cross join remaining_games rg
),

-- Expected final record using binomial distribution
expected_final_record as (
    select
        wpe.*,
        lc.playoff_teams,

        -- Expected wins = current wins + (games_remaining × win_prob)
        current_wins + (games_remaining * win_prob_per_game) as expected_final_wins,

        -- Standard deviation of remaining wins (binomial: sqrt(n*p*(1-p)))
        sqrt(
            games_remaining * win_prob_per_game * (1 - win_prob_per_game)
        ) as final_wins_stddev,

        -- Confidence intervals (±1.96 stddev for 95% CI)
        current_wins + (games_remaining * win_prob_per_game) -
            1.96 * sqrt(games_remaining * win_prob_per_game * (1 - win_prob_per_game))
            as expected_wins_lower,

        current_wins + (games_remaining * win_prob_per_game) +
            1.96 * sqrt(games_remaining * win_prob_per_game * (1 - win_prob_per_game))
            as expected_wins_upper

    from win_probability_estimate wpe
    cross join league_config lc
),

-- Approximate playoff probability
-- (This is a rough approximation; true simulation would be better)
playoff_cutoff_estimate as (
    select
        -- Estimate: Nth place team's wins (where N = playoff_teams)
        percentile_cont(1.0 - (cast(playoff_teams as double) / total_rosters))
            within group (order by expected_final_wins) as cutoff_wins
    from expected_final_record
    cross join league_config
),

final as (
    select
        efr.roster_id,
        efr.manager_name,
        efr.current_wins,
        efr.current_losses,
        efr.games_remaining,
        round(efr.win_prob_per_game, 3) as win_prob_remaining_games,
        round(efr.expected_final_wins, 1) as expected_final_wins,
        round(efr.expected_wins_lower, 1) as expected_wins_lower,
        round(efr.expected_wins_upper, 1) as expected_wins_upper,

        pce.cutoff_wins as playoff_cutoff_estimate,

        -- Playoff probability (rough approximation)
        -- P(final_wins > cutoff) using normal approximation
        round(
            1.0 / (1.0 + exp(
                -(efr.expected_final_wins - pce.cutoff_wins) /
                greatest(efr.final_wins_stddev, 0.5)
            )) * 100,
            1
        ) as playoff_probability_pct,

        case
            when efr.expected_final_wins > pce.cutoff_wins + efr.final_wins_stddev
                then 'SAFE'
            when efr.expected_final_wins > pce.cutoff_wins
                then 'LIKELY'
            when efr.expected_final_wins > pce.cutoff_wins - efr.final_wins_stddev
                then 'BUBBLE'
            else 'LONGSHOT'
        end as playoff_status

    from expected_final_record efr
    cross join playoff_cutoff_estimate pce
)

select * from final
order by playoff_probability_pct desc
```

### Step 2: Add playoff probability to dashboard

In `analytics/dashboard.py`, add a new section to the Standings page:

```python
# After line 300 (after the points visualization on Standings page)

st.markdown("---")
st.header("📊 Playoff Probability")

@st.cache_data
def load_playoff_probability(_db_mtime):
    """Load playoff probability projections"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                manager_name,
                current_wins,
                current_losses,
                games_remaining,
                round(expected_final_wins, 1) as proj_wins,
                round(playoff_probability_pct, 1) as playoff_pct,
                playoff_status
            FROM main_analytics.int_playoff_probability
            ORDER BY playoff_pct DESC
            """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load playoff probabilities: {str(e)}")
        return pd.DataFrame()

playoff_df = load_playoff_probability(get_db_mtime())

if not playoff_df.empty:
    # Playoff probability visualization
    fig = go.Figure()

    # Color by playoff status
    colors = []
    for status in playoff_df["playoff_status"]:
        if status == "SAFE":
            colors.append("#2ecc71")  # Green
        elif status == "LIKELY":
            colors.append("#3498db")  # Blue
        elif status == "BUBBLE":
            colors.append("#f39c12")  # Orange
        else:
            colors.append("#e74c3c")  # Red

    fig.add_trace(
        go.Bar(
            x=playoff_df["manager_name"],
            y=playoff_df["playoff_pct"],
            marker_color=colors,
            text=playoff_df["playoff_pct"].apply(lambda x: f"{x}%"),
            textposition="outside",
            name="Playoff %",
        )
    )

    fig.update_layout(
        title="Playoff Probability (%)",
        xaxis_title="Manager",
        yaxis_title="Playoff Probability (%)",
        yaxis_range=[0, 105],
        showlegend=False,
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Playoff probability table
    st.dataframe(
        playoff_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "current_wins": "W",
            "current_losses": "L",
            "games_remaining": "Remaining",
            "proj_wins": st.column_config.NumberColumn("Projected Wins", format="%.1f"),
            "playoff_pct": st.column_config.ProgressColumn(
                "Playoff %",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "playoff_status": "Status",
        },
    )

    st.markdown("""
    **Methodology**: Uses team scoring distributions + remaining schedule to estimate playoff odds.
    - **SAFE** (>80%): Very likely to make playoffs
    - **LIKELY** (60-80%): Favored to make playoffs
    - **BUBBLE** (40-60%): Coin flip, must win key games
    - **LONGSHOT** (<40%): Needs help + strong finish
    """)
```

## Task

1. Create `dbt/models/intermediate/int_playoff_probability.sql` with the SQL above
2. Update `analytics/dashboard.py` to add playoff probability section
3. Run DBT: `cd dbt && poetry run dbt build --select int_playoff_probability`
4. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
5. Navigate to Standings tab and verify playoff probability section appears

## Completion Criteria

- [ ] `int_playoff_probability.sql` model exists and compiles
- [ ] Dashboard shows playoff probability chart on Standings page
- [ ] Probabilities are reasonable (0-100%, sum doesn't need to equal 100%)
- [ ] Status labels (SAFE/LIKELY/BUBBLE/LONGSHOT) make sense
- [ ] All tests pass

## Validation

After implementing:

1. Check that teams with better records have higher playoff %
2. Verify SAFE teams are currently in playoff spots
3. Ensure LONGSHOT teams are mathematically alive but need miracles

---

**Note**: This is a SQL approximation of Monte Carlo simulation. For true accuracy, implement Monte Carlo in Python (future enhancement).

---

**After completing this task:**

1. Mark #10 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 10` (or manually update)
3. Move to prompt #11
