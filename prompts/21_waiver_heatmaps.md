# Enhancement: Add Waiver Wire Heatmaps & ROI Analysis

## Background

**Current**: Transaction data is ingested but not analyzed
**Missing**: "Most added/dropped players" + ROI analysis (did waiver pickups pay off?)

**Why it matters**: Waiver wire winners often decide championships. Tracking add/drop patterns reveals league sentiment and successful pickups.

## Industry Standards

- **Sleeper**: "Trending Players" widget (most added this week)
- **ESPN**: "Waiver Wire Targets" (sortable by add %)
- **Yahoo**: "Waiver Wire Activity" heatmap
- **FantasyPros**: "Waiver Wire Pickups" with ROI analysis

## Metrics to Track

### Weekly Metrics

- **Most Added**: Players claimed on waivers this week
- **Most Dropped**: Players cut this week
- **Waiver Priority Used**: Who spent FAAB/priority on whom

### ROI Metrics

- **Pickup ROI**: Average PPG after acquisition vs before
- **Best Pickups**: Waiver adds who became league winners
- **Worst Drops**: Players dropped who went off after

## Implementation

### Step 1: Analyze transaction data

**Create `dbt/models/intermediate/int_waiver_activity.sql`:**

```sql
{{ config(materialized='table') }}

/*
Waiver Wire Activity Analysis

Tracks adds/drops and measures ROI of waiver pickups.
*/

with transactions as (
    select * from {{ ref('stg_transactions') }}
    where transaction_type in ('waiver', 'free_agent')
),

player_stats as (
    select * from {{ ref('stg_player_stats') }}
),

-- Count adds per player
player_adds as (
    select
        unnest(adds) as player_id,
        week,
        roster_id,
        transaction_type,
        created_at,
        1 as add_count
    from transactions
    where adds is not null
),

-- Count drops per player
player_drops as (
    select
        unnest(drops) as player_id,
        week,
        roster_id,
        transaction_type,
        created_at,
        1 as drop_count
    from transactions
    where drops is not null
),

-- Aggregate adds/drops
waiver_summary as (
    select
        coalesce(pa.player_id, pd.player_id) as player_id,
        coalesce(pa.week, pd.week) as week,
        sum(coalesce(pa.add_count, 0)) as adds,
        sum(coalesce(pd.drop_count, 0)) as drops,
        sum(coalesce(pa.add_count, 0)) - sum(coalesce(pd.drop_count, 0)) as net_adds

    from player_adds pa
    full outer join player_drops pd
        on pa.player_id = pd.player_id
        and pa.week = pd.week
    group by
        coalesce(pa.player_id, pd.player_id),
        coalesce(pa.week, pd.week)
),

-- Join with player names
waiver_with_names as (
    select
        ws.*,
        ps.player_name,
        ps.position,
        ps.team
    from waiver_summary ws
    left join (
        select distinct player_id, player_name, position, team
        from player_stats
    ) ps on ws.player_id = ps.player_id
)

select
    player_id,
    player_name,
    position,
    team,
    week,
    adds,
    drops,
    net_adds,

    -- Trending indicator
    case
        when net_adds >= 3 then 'HOT'      -- Multiple pickups
        when net_adds >= 1 then 'RISING'   -- Net positive
        when net_adds <= -3 then 'COLD'    -- Multiple drops
        when net_adds <= -1 then 'FALLING' -- Net negative
        else 'STABLE'
    end as trend

from waiver_with_names
order by week desc, net_adds desc
```

### Step 2: Calculate waiver pickup ROI

**Create `dbt/models/marts/fct_waiver_roi.sql`:**

```sql
{{ config(materialized='table') }}

/*
Waiver Pickup ROI Analysis

Measures success of waiver pickups by comparing:
- PPG before pickup (why they were dropped)
- PPG after pickup (did they bounce back?)
*/

with waiver_adds as (
    select
        unnest(adds) as player_id,
        week as pickup_week,
        roster_id as acquiring_roster_id,
        created_at as pickup_date
    from {{ ref('stg_transactions') }}
    where transaction_type in ('waiver', 'free_agent')
      and adds is not null
),

player_stats as (
    select * from {{ ref('stg_player_stats') }}
),

-- Get performance BEFORE pickup
pre_pickup_stats as (
    select
        wa.player_id,
        wa.pickup_week,
        wa.acquiring_roster_id,
        avg(ps.weekly_points) as avg_ppg_before_pickup,
        count(*) as weeks_before

    from waiver_adds wa
    left join player_stats ps
        on wa.player_id = ps.player_id
        and ps.week < wa.pickup_week
        and ps.week >= wa.pickup_week - 3  -- Last 3 weeks before pickup
    group by wa.player_id, wa.pickup_week, wa.acquiring_roster_id
),

-- Get performance AFTER pickup
post_pickup_stats as (
    select
        wa.player_id,
        wa.pickup_week,
        wa.acquiring_roster_id,
        avg(ps.weekly_points) as avg_ppg_after_pickup,
        count(*) as weeks_after

    from waiver_adds wa
    left join player_stats ps
        on wa.player_id = ps.player_id
        and ps.week > wa.pickup_week
        and ps.week <= wa.pickup_week + 4  -- Next 4 weeks after pickup
    group by wa.player_id, wa.pickup_week, wa.acquiring_roster_id
),

-- Combine and calculate ROI
waiver_roi as (
    select
        pre.player_id,
        pre.pickup_week,
        pre.acquiring_roster_id,
        (select player_name from player_stats where player_id = pre.player_id limit 1) as player_name,
        (select position from player_stats where player_id = pre.player_id limit 1) as position,

        round(pre.avg_ppg_before_pickup, 2) as avg_ppg_before,
        round(post.avg_ppg_after_pickup, 2) as avg_ppg_after,
        round(post.avg_ppg_after_pickup - pre.avg_ppg_before_pickup, 2) as ppg_improvement,

        post.weeks_after,

        -- ROI classification
        case
            when post.avg_ppg_after_pickup - pre.avg_ppg_before_pickup >= 5
                then 'LEAGUE_WINNER'  -- +5 PPG improvement
            when post.avg_ppg_after_pickup - pre.avg_ppg_before_pickup >= 2
                then 'GREAT_PICKUP'   -- +2-5 PPG
            when post.avg_ppg_after_pickup - pre.avg_ppg_before_pickup >= 0
                then 'DECENT_PICKUP'  -- Positive
            when post.avg_ppg_after_pickup - pre.avg_ppg_before_pickup >= -2
                then 'BUST'           -- Slight negative
            else 'DISASTER'            -- -2+ PPG (worse than before)
        end as pickup_verdict

    from pre_pickup_stats pre
    left join post_pickup_stats post
        on pre.player_id = post.player_id
        and pre.pickup_week = post.pickup_week
        and pre.acquiring_roster_id = post.acquiring_roster_id
    where post.weeks_after >= 2  -- Need at least 2 weeks after pickup to evaluate
)

select * from waiver_roi
order by ppg_improvement desc
```

### Step 3: Add to dashboard

Create a new "Waiver Wire" page:

```python
# In dashboard.py, add to sidebar navigation

page = st.radio(
    "Choose a view:",
    [
        "📊 Standings",
        "🤓 Luck Analysis",
        "📈 Weekly Performance",
        "🎯 Draft Analysis",
        "🔥 Waiver Wire",  # NEW
    ],
)

# Add waiver wire page
elif page == "🔥 Waiver Wire":
    st.header("🔥 Waiver Wire Analysis")

    st.markdown("""
    Track waiver wire adds/drops and measure the ROI of pickups.
    Who found the hidden gems? Who dropped league winners?
    """)

    # Current week trending
    st.subheader("📈 Trending This Week")

    @st.cache_data
    def load_waiver_activity(_db_mtime):
        """Load waiver wire activity"""
        try:
            conn = get_db_connection(_db_mtime)
            return conn.execute(
                """
                SELECT
                    player_name,
                    position,
                    team,
                    adds,
                    drops,
                    net_adds,
                    trend
                FROM main_analytics.int_waiver_activity
                WHERE week = (SELECT MAX(week) FROM main_analytics.int_waiver_activity)
                ORDER BY net_adds DESC
                """
            ).df()
        except Exception as e:
            st.error(f"⚠️ Could not load waiver activity: {str(e)}")
            return pd.DataFrame()

    waiver_df = load_waiver_activity(get_db_mtime())

    if not waiver_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔥 Most Added")
            most_added = waiver_df.nlargest(10, "adds")
            st.dataframe(
                most_added[["player_name", "position", "adds", "trend"]],
                hide_index=True,
            )

        with col2:
            st.markdown("### 💔 Most Dropped")
            most_dropped = waiver_df.nlargest(10, "drops")
            st.dataframe(
                most_dropped[["player_name", "position", "drops", "trend"]],
                hide_index=True,
            )

    # Waiver ROI analysis
    st.markdown("---")
    st.subheader("💰 Waiver Pickup ROI")

    @st.cache_data
    def load_waiver_roi(_db_mtime):
        """Load waiver pickup ROI"""
        try:
            conn = get_db_connection(_db_mtime)
            return conn.execute(
                """
                SELECT
                    player_name,
                    position,
                    pickup_week,
                    avg_ppg_before,
                    avg_ppg_after,
                    ppg_improvement,
                    pickup_verdict
                FROM main_analytics.fct_waiver_roi
                ORDER BY ppg_improvement DESC
                """
            ).df()
        except Exception as e:
            st.error(f"⚠️ Could not load waiver ROI: {str(e)}")
            return pd.DataFrame()

    roi_df = load_waiver_roi(get_db_mtime())

    if not roi_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🏆 Best Pickups")
            best_pickups = roi_df[
                roi_df["pickup_verdict"].isin(["LEAGUE_WINNER", "GREAT_PICKUP"])
            ].head(10)

            st.dataframe(
                best_pickups,
                hide_index=True,
                column_config={
                    "player_name": "Player",
                    "position": "Pos",
                    "pickup_week": "Week",
                    "avg_ppg_before": st.column_config.NumberColumn("Before", format="%.1f"),
                    "avg_ppg_after": st.column_config.NumberColumn("After", format="%.1f"),
                    "ppg_improvement": st.column_config.NumberColumn("+/-", format="%+.1f"),
                    "pickup_verdict": "Verdict",
                },
            )

        with col2:
            st.markdown("### 💸 Worst Pickups")
            worst_pickups = roi_df[
                roi_df["pickup_verdict"].isin(["BUST", "DISASTER"])
            ].head(10)

            st.dataframe(
                worst_pickups,
                hide_index=True,
                column_config={
                    "player_name": "Player",
                    "position": "Pos",
                    "pickup_week": "Week",
                    "avg_ppg_before": st.column_config.NumberColumn("Before", format="%.1f"),
                    "avg_ppg_after": st.column_config.NumberColumn("After", format="%.1f"),
                    "ppg_improvement": st.column_config.NumberColumn("+/-", format="%+.1f"),
                    "pickup_verdict": "Verdict",
                },
            )

        st.markdown("""
        **💡 How to use:**
        - **LEAGUE_WINNER**: +5 PPG improvement (championship-altering pickup)
        - **GREAT_PICKUP**: +2-5 PPG (strong waiver move)
        - **BUST/DISASTER**: Negative ROI (wasted waiver priority)
        """)
```

## Task

1. Create `int_waiver_activity.sql`
2. Create `fct_waiver_roi.sql`
3. Add waiver wire page to dashboard
4. Run DBT: `cd dbt && poetry run dbt build`
5. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
6. Navigate to "Waiver Wire" tab

## Completion Criteria

- [ ] Waiver activity tracked (adds/drops per player)
- [ ] ROI calculated (PPG before vs after pickup)
- [ ] Dashboard shows trending players and pickup success rate
- [ ] All tests pass

## Validation Query

```sql
SELECT
    player_name,
    position,
    adds,
    drops,
    net_adds,
    trend
FROM main_analytics.int_waiver_activity
WHERE week = (SELECT MAX(week) FROM main_analytics.int_waiver_activity)
ORDER BY net_adds DESC
LIMIT 10;
```

Expected: Should see recently hot players (injury replacements, breakouts).

---

**Future Enhancements:**

- FAAB spending analysis (if league uses FAAB)
- Waiver priority tracking
- Team-level waiver success rate (who makes best pickups?)

---

**After completing this task:**

1. Mark #21 as done in `CODE_REVIEW_PROGRESS.md`
2. **Celebrate!** 🎉 You've completed all 21 code review items!
3. Consider writing a blog post about your analytics platform
