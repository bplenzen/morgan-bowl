# Enhancement: Add Playoff Strength of Schedule (Weeks 15-17)

## Background

**Current**: General schedule luck (season-long average opponent strength)
**Missing**: **Playoff-specific SOS** for weeks 15-17 (the most important weeks!)

**Why it matters**: A team at 7-1 might have:

- Easy path to playoffs ✅
- **But brutal playoff matchups** (3 top-5 defenses in weeks 15-17) ❌

Playoff SOS helps identify championship traps.

## Industry Standards

- **FantasyPros**: "Playoff SOS" charts (updated weekly, color-coded)
- **ESPN**: Shows "Strength of Schedule" with separate playoff view
- **Sleeper**: Trending "easy/hard playoff schedule" badges
- **4for4**: Playoff matchup charts (who faces whom in championship weeks)

## Implementation

### Step 1: Create playoff SOS model

**Create `dbt/models/intermediate/int_playoff_sos.sql`:**

```sql
{{ config(materialized='table') }}

/*
Playoff Strength of Schedule (Weeks 15-17)

Analyzes opponent strength during fantasy playoffs.
Helps identify players with favorable/brutal playoff matchups.
*/

with league_config as (
    select
        playoff_week_start,
        playoff_week_start + 2 as championship_week  -- Typically week 17
    from {{ ref('stg_league') }}
),

matchups as (
    select * from {{ ref('stg_matchups') }}
),

rosters as (
    select * from {{ ref('stg_rosters') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

-- Get average points allowed by each team (defensive strength)
defensive_strength as (
    select
        m2.roster_id as defense_roster_id,
        avg(m1.points) as avg_points_allowed,
        stddev(m1.points) as stddev_points_allowed,
        count(*) as games_played

    from matchups m1
    inner join matchups m2
        on m1.week = m2.week
        and m1.matchup_id = m2.matchup_id
        and m1.roster_id != m2.roster_id
    group by m2.roster_id
),

-- Get playoff schedule (who faces whom in weeks 15-17)
playoff_schedule as (
    select
        m1.roster_id,
        m1.week,
        m2.roster_id as opponent_roster_id,
        ds.avg_points_allowed as opponent_avg_pa,
        ds.stddev_points_allowed as opponent_pa_stddev

    from matchups m1
    inner join matchups m2
        on m1.week = m2.week
        and m1.matchup_id = m2.matchup_id
        and m1.roster_id != m2.roster_id
    left join defensive_strength ds
        on m2.roster_id = ds.defense_roster_id
    cross join league_config lc
    where m1.week >= lc.playoff_week_start
      and m1.week <= lc.championship_week
),

-- Aggregate playoff SOS
playoff_sos_metrics as (
    select
        ps.roster_id,
        count(distinct ps.week) as playoff_weeks,
        round(avg(ps.opponent_avg_pa), 2) as avg_playoff_opponent_strength,
        round(stddev(ps.opponent_avg_pa), 2) as playoff_schedule_variance,

        -- Week-by-week breakdown
        max(case when ps.week = 15 then ps.opponent_avg_pa end) as week15_opponent_strength,
        max(case when ps.week = 16 then ps.opponent_avg_pa end) as week16_opponent_strength,
        max(case when ps.week = 17 then ps.opponent_avg_pa end) as week17_opponent_strength

    from playoff_schedule ps
    group by ps.roster_id
),

-- Rank teams by playoff SOS difficulty
ranked_playoff_sos as (
    select
        *,
        row_number() over (order by avg_playoff_opponent_strength) as playoff_sos_rank,

        -- Tier classification
        case
            when avg_playoff_opponent_strength >= (
                select percentile_cont(0.75) within group (order by avg_playoff_opponent_strength)
                from playoff_sos_metrics
            ) then 'BRUTAL'
            when avg_playoff_opponent_strength >= (
                select percentile_cont(0.50) within group (order by avg_playoff_opponent_strength)
                from playoff_sos_metrics
            ) then 'TOUGH'
            when avg_playoff_opponent_strength >= (
                select percentile_cont(0.25) within group (order by avg_playoff_opponent_strength)
                from playoff_sos_metrics
            ) then 'MODERATE'
            else 'EASY'
        end as playoff_sos_tier

    from playoff_sos_metrics
)

select
    rps.roster_id,
    (select display_name from {{ ref('stg_users') }} u
     inner join {{ ref('stg_rosters') }} r on u.user_id = r.owner_id
     where r.roster_id = rps.roster_id) as manager_name,

    rps.playoff_weeks,
    rps.avg_playoff_opponent_strength,
    rps.week15_opponent_strength,
    rps.week16_opponent_strength,
    rps.week17_opponent_strength,
    rps.playoff_sos_rank,
    rps.playoff_sos_tier,

    -- Compare to season-long SOS
    (
        select round(avg(opponent_avg_pa), 2)
        from defensive_strength
    ) as league_avg_defense,

    -- Playoff advantage/disadvantage
    round(
        rps.avg_playoff_opponent_strength -
        (select avg(avg_playoff_opponent_strength) from playoff_sos_metrics),
        2
    ) as playoff_sos_differential

from ranked_playoff_sos rps
order by rps.playoff_sos_rank
```

### Step 2: Add playoff SOS to dashboard

Add a new section to Standings page or create dedicated Playoff page:

```python
# In dashboard.py, add to Standings page (after playoff probability)

st.markdown("---")
st.subheader("📅 Playoff Schedule Strength (Weeks 15-17)")

@st.cache_data
def load_playoff_sos(_db_mtime):
    """Load playoff strength of schedule"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                manager_name,
                avg_playoff_opponent_strength,
                week15_opponent_strength,
                week16_opponent_strength,
                week17_opponent_strength,
                playoff_sos_tier,
                playoff_sos_differential
            FROM main_analytics.int_playoff_sos
            ORDER BY avg_playoff_opponent_strength
            """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load playoff SOS: {str(e)}")
        return pd.DataFrame()

playoff_sos_df = load_playoff_sos(get_db_mtime())

if not playoff_sos_df.empty:
    st.markdown("""
    **Playoff SOS measures opponent strength during championship weeks (15-17).**

    - 🟢 **Easy**: Face weak opponents in playoffs (advantage)
    - 🟡 **Moderate**: Average playoff matchups
    - 🟠 **Tough**: Face strong opponents
    - 🔴 **Brutal**: Nightmare playoff schedule (sell assets before playoffs?)
    """)

    # Color-code by tier
    def color_sos_tier(val):
        if val == "EASY":
            return "background-color: #2ecc71; color: white"
        elif val == "MODERATE":
            return "background-color: #f39c12; color: white"
        elif val == "TOUGH":
            return "background-color: #e67e22; color: white"
        else:  # BRUTAL
            return "background-color: #e74c3c; color: white"

    styled_sos = playoff_sos_df.style.applymap(
        color_sos_tier,
        subset=["playoff_sos_tier"]
    )

    st.dataframe(
        styled_sos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "avg_playoff_opponent_strength": st.column_config.NumberColumn(
                "Avg Playoff Opp",
                format="%.2f",
                help="Average points allowed by playoff opponents (lower = easier)"
            ),
            "week15_opponent_strength": st.column_config.NumberColumn(
                "Week 15", format="%.1f"
            ),
            "week16_opponent_strength": st.column_config.NumberColumn(
                "Week 16", format="%.1f"
            ),
            "week17_opponent_strength": st.column_config.NumberColumn(
                "Week 17 (Ship)", format="%.1f"
            ),
            "playoff_sos_tier": "SOS Tier",
            "playoff_sos_differential": st.column_config.NumberColumn(
                "vs League Avg",
                format="%+.2f",
                help="Positive = harder than average, negative = easier"
            ),
        },
    )

    # Visualization: Playoff SOS heatmap
    st.subheader("Playoff Matchup Heatmap")

    fig = go.Figure()

    for idx, row in playoff_sos_df.iterrows():
        fig.add_trace(go.Bar(
            name=row["manager_name"],
            x=["Week 15", "Week 16", "Week 17"],
            y=[
                row["week15_opponent_strength"],
                row["week16_opponent_strength"],
                row["week17_opponent_strength"],
            ],
            marker_color=[
                "#2ecc71" if row["week15_opponent_strength"] < playoff_sos_df["week15_opponent_strength"].median() else "#e74c3c",
                "#2ecc71" if row["week16_opponent_strength"] < playoff_sos_df["week16_opponent_strength"].median() else "#e74c3c",
                "#2ecc71" if row["week17_opponent_strength"] < playoff_sos_df["week17_opponent_strength"].median() else "#e74c3c",
            ],
        ))

    fig.update_layout(
        title="Playoff Opponent Strength by Week",
        xaxis_title="Playoff Week",
        yaxis_title="Opponent Avg Points Allowed",
        barmode="group",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **💡 Strategy Tips:**
    - **Easy playoff SOS**: Championship path is clear, hold your roster
    - **Brutal playoff SOS**: Consider trading playoff starters for draft picks (dynasty) or consolidating talent
    - **Week 17 matters most**: Focus on championship week matchup
    """)
```

## Task

1. Create `dbt/models/intermediate/int_playoff_sos.sql`
2. Update `analytics/dashboard.py` to add playoff SOS section
3. Run DBT: `cd dbt && poetry run dbt build --select int_playoff_sos`
4. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
5. Navigate to Standings → Playoff Schedule Strength

## Completion Criteria

- [ ] Playoff SOS calculated for weeks 15-17
- [ ] Dashboard shows tier-coded playoff schedules (Easy/Moderate/Tough/Brutal)
- [ ] Heatmap visualization shows week-by-week matchups
- [ ] All tests pass

## Validation Query

```sql
SELECT
    manager_name,
    avg_playoff_opponent_strength,
    playoff_sos_tier,
    week15_opponent_strength,
    week16_opponent_strength,
    week17_opponent_strength
FROM main_analytics.int_playoff_sos
ORDER BY avg_playoff_opponent_strength;
```

Expected: Teams with easy playoff schedules should have lower avg_playoff_opponent_strength.

---

**Industry Reference:**

- FantasyPros "Playoff SOS" tool: <https://www.fantasypros.com/nfl/strength-of-schedule.php>
- Shows color-coded matchups for each position

---

**After completing this task:**

1. Mark #18 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 18` (or manually update)
3. Move to prompt #19
