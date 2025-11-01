# Enhancement: Add Spike Weeks Metric (JJ Zachariason Method)

## Background

**JJ Zachariason** (Late Round Podcast) showed that **"spike weeks"** (top-12 positional finishes) predict playoff success better than average PPG.

**Why it matters**: A WR averaging 12 PPG with 4 spike weeks (WR1 performances) is more valuable for playoffs than a WR averaging 14 PPG with 0 spike weeks (consistent floor but no ceiling).

Boom-bust players can win championships even with mediocre season averages.

## Current Metrics

- Average PPG ✅
- Standard deviation ✅
- Consistency tier ✅
- Boom/bust rates ✅

## Missing Metric

**Spike Weeks**: Number of weeks a player finished top-12 at their position.

This complements boom rate (top 90th percentile for that player) with position-relative performance (top-12 at position league-wide).

## Implementation

### Step 1: Add spike weeks to int_player_weekly_variance.sql

Update `dbt/models/intermediate/int_player_weekly_variance.sql`:

```sql
-- After line 54 (in weekly_performance CTE), add positional rank per week

weekly_performance_with_rank as (
    select
        wp.*,
        -- Rank within position for each week
        row_number() over (
            partition by wp.week, wp.position
            order by wp.weekly_points desc
        ) as weekly_position_rank
    from weekly_performance wp
),

-- Update subsequent CTEs to use weekly_performance_with_rank instead of weekly_performance

-- Then add spike weeks calculation in the variance_metrics CTE (around line 80)
-- Add this after bust_rate_pct:

-- SPIKE WEEKS: Top-12 positional finishes (WR1/RB1 performances)
count(case when weekly_position_rank <= 12 then 1 end) as spike_weeks,
round(
    count(case when weekly_position_rank <= 12 then 1 end)::double / count(*) * 100,
    1
) as spike_week_rate_pct,

-- Top-6 finishes (true WR1/RB1 weeks)
count(case when weekly_position_rank <= 6 then 1 end) as elite_spike_weeks,

-- Average rank when they spike (quality of spike weeks)
round(
    avg(case when weekly_position_rank <= 12 then weekly_position_rank end),
    1
) as avg_spike_rank
```

Full context - replace the `weekly_performance` CTE and add the ranking:

```sql
-- Around line 20-30, update to:
weekly_performance_with_rank as (
    select
        ps.player_id,
        ps.player_name,
        ps.position,
        ps.team,
        ps.week,
        ps.weekly_points,
        -- Positional rank for this week
        row_number() over (
            partition by ps.week, ps.position
            order by ps.weekly_points desc
        ) as weekly_position_rank
    from player_stats ps
    where ps.position in ('QB', 'RB', 'WR', 'TE')
),

-- Then in variance_metrics CTE (around line 70-90), add spike metrics:
variance_metrics as (
    select
        player_id,
        player_name,
        position,
        count(distinct week) as weeks_played,
        round(avg(weekly_points), 2) as avg_weekly_points,
        round(stddev(weekly_points), 2) as stddev_weekly_points,
        -- ... existing metrics ...

        -- SPIKE WEEKS (NEW)
        count(case when weekly_position_rank <= 12 then 1 end) as spike_weeks,
        round(
            count(case when weekly_position_rank <= 12 then 1 end)::double / count(*) * 100,
            1
        ) as spike_week_rate_pct,
        count(case when weekly_position_rank <= 6 then 1 end) as elite_spike_weeks,
        round(
            avg(case when weekly_position_rank <= 12 then weekly_position_rank end),
            1
        ) as avg_spike_rank

    from weekly_performance_with_rank
    group by player_id, player_name, position
)
```

### Step 2: Add spike week tier classification

In the same file, add spike tier logic (around line 120):

```sql
-- SPIKE TIER: How often does this player deliver WR1/RB1 weeks?
case
    when spike_week_rate_pct >= 50 then 'ELITE_SPIKER'       -- 50%+ spike weeks
    when spike_week_rate_pct >= 35 then 'STRONG_SPIKER'      -- 35-50%
    when spike_week_rate_pct >= 20 then 'MODERATE_SPIKER'    -- 20-35%
    when spike_week_rate_pct >= 10 then 'OCCASIONAL_SPIKER'  -- 10-20%
    else 'LOW_SPIKE'                                          -- <10%
end as spike_tier,

-- Championship upside flag (elite spike weeks)
elite_spike_weeks >= 3 as championship_upside
```

### Step 3: Update dashboard to display spike weeks

In `analytics/dashboard.py`, add spike weeks to draft analysis:

```python
# Update load_draft_performance query (around line 172-210) to include:
@st.cache_data
def load_draft_performance(_db_mtime):
    """Load draft analysis with grades and metrics (including spike weeks)"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                -- ... existing fields ...
                games_played,

                -- NEW: Spike weeks from variance metrics
                (SELECT spike_weeks FROM main_analytics.int_player_weekly_variance wpv
                 WHERE wpv.player_id = dp.player_id) as spike_weeks,
                (SELECT spike_week_rate_pct FROM main_analytics.int_player_weekly_variance wpv
                 WHERE wpv.player_id = dp.player_id) as spike_rate,
                (SELECT elite_spike_weeks FROM main_analytics.int_player_weekly_variance wpv
                 WHERE wpv.player_id = dp.player_id) as elite_spikes

            FROM main_analytics.fct_draft_performance dp
            ORDER BY pick_no
            """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load draft analysis: {str(e)}")
        return pd.DataFrame()
```

Add spike weeks section to draft analysis (after Advanced Metrics Breakdown, around line 1243):

```python
with st.expander("🔥 Spike Weeks Analysis (Championship Upside)"):
    st.markdown("""
    **Spike Weeks**: Games where a player finished top-12 at their position.

    Research by JJ Zachariason shows spike weeks predict playoff success better than average PPG.
    A boom-bust player with 4 spike weeks can win championships despite mediocre season average.
    """)

    spike_df = filtered_df[
        (filtered_df["games_played"] >= 5) &
        (filtered_df["spike_weeks"].notna())
    ].sort_values("spike_weeks", ascending=False)

    st.dataframe(
        spike_df[
            [
                "player_name",
                "position_display",
                "games_played",
                "spike_weeks",
                "spike_rate",
                "elite_spikes",
                "adj_vor",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "player_name": "Player",
            "position_display": "Pos",
            "games_played": "GP",
            "spike_weeks": st.column_config.NumberColumn(
                "Spike Weeks",
                help="Times finished top-12 at position",
            ),
            "spike_rate": st.column_config.NumberColumn(
                "Spike %",
                format="%.1f%%",
                help="Percentage of games with top-12 finish",
            ),
            "elite_spikes": st.column_config.NumberColumn(
                "Elite Spikes",
                help="Times finished top-6 at position (true WR1/RB1 weeks)",
            ),
            "adj_vor": st.column_config.NumberColumn("VOR", format="%.1f"),
        },
    )
```

## Task

1. Read `dbt/models/intermediate/int_player_weekly_variance.sql`
2. Add weekly positional ranking and spike week calculations
3. Update `analytics/dashboard.py` to display spike weeks
4. Run DBT: `cd dbt && poetry run dbt build --select int_player_weekly_variance fct_draft_performance`
5. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
6. Navigate to Draft Analysis → Spike Weeks Analysis (expandable)

## Completion Criteria

- [ ] Spike weeks calculated in int_player_weekly_variance.sql
- [ ] Dashboard displays spike weeks in expandable section
- [ ] Spike rate % shows how often players deliver WR1/RB1 weeks
- [ ] All tests pass

## Validation Query

After implementing, verify spike weeks are reasonable:

```sql
SELECT
    player_name,
    position,
    weeks_played,
    spike_weeks,
    spike_week_rate_pct,
    elite_spike_weeks
FROM main_analytics.int_player_weekly_variance
WHERE weeks_played >= 8
ORDER BY spike_weeks DESC
LIMIT 20;
```

Expected: Top players should have 4-6 spike weeks, elite players 2-4 elite spikes.

---

**Reference:**

- JJ Zachariason's research: Late Round Podcast, "Spike Weeks Win Championships"
- Industry adoption: 4for4, Establish The Run, FantasyPros all show this metric

---

**After completing this task:**

1. Mark #11 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 11` (or manually update)
3. Move to prompt #12
