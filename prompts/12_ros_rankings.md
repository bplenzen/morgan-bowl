# Enhancement: Add Rest-of-Season (ROS) Rankings

## Background

**Current**: Only season-long ranks (`current_rank_position` shows cumulative performance)
**Missing**: Rest-of-season projections that weight recent games + adjust for schedule/injuries

**Why it matters**: In Week 10, a player who just returned from injury might have:

- Season rank: RB30 (dragged down by missed games)
- **ROS rank: RB8** (healthy, favorable schedule, increased role)

ROS rankings are critical for trade decisions and lineup optimization.

## Industry Standards

- **FantasyPros**: "ROS Rank" updated weekly
- **ESPN**: "Outlook Rank" (forward-looking)
- **Yahoo**: "Rest of Season" projections
- **Sleeper**: Shows "trending up/down" based on recent performance

## Implementation Approach

Use **exponentially weighted moving average (EWMA)** to emphasize recent weeks + adjust for remaining schedule strength.

### Step 1: Create ROS rankings model

**Create `dbt/models/intermediate/int_ros_player_rankings.sql`:**

```sql
{{ config(materialized='table') }}

/*
Rest-of-Season (ROS) Player Rankings

Methodology:
1. Weight recent games more heavily (exponential decay)
2. Adjust for remaining schedule difficulty
3. Apply injury discount factor (if applicable)
4. Calculate expected PPG for rest of season

This is forward-looking, unlike current_rank_position (backward-looking).
*/

with player_stats as (
    select * from {{ ref('stg_player_stats') }}
),

matchups as (
    select * from {{ ref('stg_matchups') }}
),

league_config as (
    select playoff_week_start from {{ ref('stg_league') }}
),

-- Get weeks played and current week
weeks_metadata as (
    select
        max(week) as current_week,
        (select playoff_week_start from league_config) as playoff_week
    from matchups
),

-- Recent performance (last 4 weeks weighted more heavily)
recent_performance as (
    select
        player_id,
        player_name,
        position,
        team,
        week,
        weekly_points,

        -- Exponential weight: more recent = higher weight
        -- Weight formula: 2^(week - max_week + 4) so last 4 weeks = [8, 4, 2, 1]
        power(2, week - (select current_week from weeks_metadata) + 4) as week_weight

    from player_stats
    where position in ('QB', 'RB', 'WR', 'TE')
      -- Only use last 6 weeks for ROS projection
      and week >= (select current_week from weeks_metadata) - 5
),

-- Weighted average PPG (emphasizes recent performance)
weighted_ppg as (
    select
        player_id,
        player_name,
        position,
        team,
        count(*) as recent_games,

        -- Weighted average: sum(points × weight) / sum(weight)
        round(
            sum(weekly_points * week_weight) / sum(week_weight),
            2
        ) as ros_projected_ppg,

        -- Compare to unweighted average
        round(avg(weekly_points), 2) as recent_avg_ppg,

        -- Variance in recent games (uncertainty)
        round(stddev(weekly_points), 2) as recent_stddev

    from recent_performance
    group by player_id, player_name, position, team
    having count(*) >= 3  -- Minimum 3 games for ROS projection
),

-- Injury/availability discount (players who missed recent games)
availability_adjustment as (
    select
        player_id,
        count(*) as weeks_active_last_6,

        -- Discount factor for players who missed games
        case
            when count(*) >= 5 then 1.00   -- Fully available
            when count(*) = 4 then 0.95    -- Missed 1-2 games, slight concern
            when count(*) = 3 then 0.90    -- Missed 3 games, moderate concern
            else 0.85                       -- Missed 4+ games, high risk
        end as availability_factor

    from player_stats
    where week >= (select current_week from weeks_metadata) - 5
      and position in ('QB', 'RB', 'WR', 'TE')
    group by player_id
),

-- Combine weighted PPG with availability adjustment
ros_projections as (
    select
        wpg.player_id,
        wpg.player_name,
        wpg.position,
        wpg.team,
        wpg.recent_games,
        wpg.ros_projected_ppg,
        aa.availability_factor,

        -- Final ROS PPG: weighted average × availability
        round(wpg.ros_projected_ppg * aa.availability_factor, 2)
            as ros_adjusted_ppg,

        wpg.recent_stddev

    from weighted_ppg wpg
    left join availability_adjustment aa
        on wpg.player_id = aa.player_id
),

-- Rank players by ROS projected PPG
ros_rankings as (
    select
        *,
        row_number() over (order by ros_adjusted_ppg desc) as ros_rank_overall,
        row_number() over (
            partition by position
            order by ros_adjusted_ppg desc
        ) as ros_rank_position,

        -- ROS tier (for quick comparison)
        case
            when row_number() over (partition by position order by ros_adjusted_ppg desc) <= 6
                then 'ELITE'
            when row_number() over (partition by position order by ros_adjusted_ppg desc) <= 12
                then 'WR1/RB1'
            when row_number() over (partition by position order by ros_adjusted_ppg desc) <= 24
                then 'WR2/RB2'
            when row_number() over (partition by position order by ros_adjusted_ppg desc) <= 36
                then 'FLEX'
            else 'BENCH'
        end as ros_tier

    from ros_projections
)

select
    player_id,
    player_name,
    position,
    team,
    recent_games,
    ros_projected_ppg,
    availability_factor,
    ros_adjusted_ppg,
    recent_stddev,
    ros_rank_overall,
    ros_rank_position,
    ros_tier,

    -- Confidence in projection (more games = more confident)
    case
        when recent_games >= 5 then 'HIGH'
        when recent_games >= 4 then 'MODERATE'
        else 'LOW'
    end as projection_confidence

from ros_rankings
order by ros_rank_overall
```

### Step 2: Add ROS comparison to current rankings

Update dashboard to show season rank vs ROS rank side-by-side:

```python
# In dashboard.py, add a new comparison section (after Weekly Performance, around line 680)

elif page == "📈 Rest-of-Season Rankings":
    st.header("📈 Rest-of-Season (ROS) Projections")

    st.markdown("""
    **ROS rankings weight recent performance more heavily** and adjust for availability.
    Use these for trade decisions and rest-of-season lineup planning.

    - **Trending Up 🔥**: ROS rank >> Season rank (buy low candidate)
    - **Trending Down ❄️**: ROS rank << Season rank (sell high candidate)
    """)

    @st.cache_data
    def load_ros_rankings(_db_mtime):
        """Load rest-of-season projections"""
        try:
            conn = get_db_connection(_db_mtime)
            return conn.execute(
                """
                SELECT
                    ros.player_name,
                    ros.position,
                    ros.team,
                    ros.ros_rank_position as ros_rank,
                    cr.current_rank_position as season_rank,
                    ros.ros_rank_position - cr.current_rank_position as rank_change,
                    ros.ros_adjusted_ppg as ros_ppg,
                    cr.points_per_game as season_ppg,
                    ros.projection_confidence,
                    ros.ros_tier
                FROM main_analytics.int_ros_player_rankings ros
                LEFT JOIN main_analytics.int_current_player_rankings cr
                    ON ros.player_id = cr.player_id
                WHERE ros.recent_games >= 3
                ORDER BY ros.ros_rank_position
                """
            ).df()
        except Exception as e:
            st.error(f"⚠️ Could not load ROS rankings: {str(e)}")
            return pd.DataFrame()

    ros_df = load_ros_rankings(get_db_mtime())

    if not ros_df.empty:
        # Position filter
        positions = ["All"] + sorted(ros_df["position"].unique().tolist())
        selected_position = st.selectbox("Filter by Position:", positions)

        if selected_position != "All":
            ros_df = ros_df[ros_df["position"] == selected_position]

        # Add trend indicator
        ros_df["trend"] = ros_df["rank_change"].apply(
            lambda x: "🔥 Trending Up" if x < -5
            else "❄️ Trending Down" if x > 5
            else "➡️ Steady"
        )

        # Display table
        st.dataframe(
            ros_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "player_name": "Player",
                "position": "Pos",
                "team": "Team",
                "season_rank": st.column_config.NumberColumn("Season Rank"),
                "ros_rank": st.column_config.NumberColumn("ROS Rank"),
                "rank_change": st.column_config.NumberColumn(
                    "Change",
                    help="Negative = trending up, Positive = trending down",
                    format="%+d",
                ),
                "season_ppg": st.column_config.NumberColumn("Season PPG", format="%.1f"),
                "ros_ppg": st.column_config.NumberColumn("ROS PPG", format="%.1f"),
                "projection_confidence": "Confidence",
                "ros_tier": "ROS Tier",
                "trend": "Trend",
            },
        )

        # Biggest risers and fallers
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔥 Biggest Risers (Buy Low)")
            risers = ros_df.nsmallest(10, "rank_change")
            st.dataframe(
                risers[["player_name", "position", "season_rank", "ros_rank", "rank_change"]],
                hide_index=True,
            )

        with col2:
            st.subheader("❄️ Biggest Fallers (Sell High)")
            fallers = ros_df.nlargest(10, "rank_change")
            st.dataframe(
                fallers[["player_name", "position", "season_rank", "ros_rank", "rank_change"]],
                hide_index=True,
            )
```

### Step 3: Update sidebar navigation

```python
# Update sidebar navigation (around line 223-231)
page = st.radio(
    "Choose a view:",
    [
        "📊 Standings",
        "🤓 Luck Analysis",
        "📈 Weekly Performance",
        "🎯 Draft Analysis",
        "📈 Rest-of-Season Rankings",  # NEW
    ],
)
```

## Task

1. Create `dbt/models/intermediate/int_ros_player_rankings.sql`
2. Update `analytics/dashboard.py` to add ROS rankings page
3. Run DBT: `cd dbt && poetry run dbt build --select int_ros_player_rankings`
4. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
5. Navigate to "Rest-of-Season Rankings" tab

## Completion Criteria

- [ ] ROS rankings model exists and uses EWMA weighting
- [ ] Dashboard shows ROS rankings with trend indicators
- [ ] Biggest risers/fallers sections help identify trade targets
- [ ] All tests pass

## Validation Query

```sql
SELECT
    player_name,
    position,
    season_rank,
    ros_rank,
    rank_change,
    ros_ppg
FROM (
    SELECT
        ros.player_name,
        ros.position,
        cr.current_rank_position as season_rank,
        ros.ros_rank_position as ros_rank,
        ros.ros_rank_position - cr.current_rank_position as rank_change,
        ros.ros_adjusted_ppg as ros_ppg
    FROM main_analytics.int_ros_player_rankings ros
    LEFT JOIN main_analytics.int_current_player_rankings cr
        ON ros.player_id = cr.player_id
)
WHERE position = 'RB'
ORDER BY abs(rank_change) DESC
LIMIT 10;
```

Expected: Should see some RBs trending up (recently returned from injury) and some trending down (recent slump).

---

**After completing this task:**

1. Mark #12 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 12` (or manually update)
3. Move to prompt #13
