# Enhancement: Add Trade Analyzer Tool

## Background

Trade analysis is the **#1 feature request** on every fantasy platform's subreddit.

**Current**: No trade evaluation tools
**Needed**: "Is trading Saquon Barkley for CeeDee Lamb + Travis Kelce fair?"

## Why This Matters

League members ask "should I accept this trade?" constantly. Having a built-in analyzer:

1. Prevents lopsided trades (preserves league competitive balance)
2. Helps casual players make informed decisions
3. Drives engagement (users check the tool frequently)

## Industry Standards

- **KeepTradeCut.com**: Crowdsourced trade values (updated daily, 100k+ users)
- **FantasyPros Trade Analyzer**: VOR-based + expert consensus + crowdsourcing
- **Sleeper**: Built-in trade value chart (updated weekly)
- **Dynasty Trade Analyzer**: GitHub repo with open-source implementation

## Implementation (MVP)

### Phase 1: Simple VOR-Based Trade Analyzer

**Create `dbt/models/marts/fct_trade_values.sql`:**

```sql
{{ config(materialized='table') }}

/*
Trade Value Calculator

Methodology:
1. Base value = Risk-adjusted VOR (already calculated)
2. Position scarcity adjustment (TE/RB worth more than WR/QB)
3. Roster context (is team giving up depth or starting lineup?)
4. ROS projection (future value, not past performance)

This provides a **baseline** for trade discussions, not gospel truth.
*/

with player_rankings as (
    select
        player_id,
        player_name,
        position,
        current_rank_position,
        points_per_game,
        games_played
    from {{ ref('int_current_player_rankings') }}
),

draft_performance as (
    select
        player_id,
        risk_adjusted_scarcity_vor,
        vor_tier_label,
        consistency_tier,
        risk_tier
    from {{ ref('fct_draft_performance') }}
),

-- ROS rankings for forward-looking value
ros_rankings as (
    select
        player_id,
        ros_rank_position,
        ros_adjusted_ppg,
        projection_confidence
    from {{ ref('int_ros_player_rankings') }}
),

-- Calculate trade value score
trade_values as (
    select
        pr.player_id,
        pr.player_name,
        pr.position,
        pr.current_rank_position,
        dp.risk_adjusted_scarcity_vor as current_vor,
        ros.ros_rank_position,
        ros.ros_adjusted_ppg,

        -- Trade value = weighted average of current VOR and ROS projection
        -- 40% current performance, 60% ROS projection (future value matters more)
        round(
            (dp.risk_adjusted_scarcity_vor * 0.4) +
            (ros.ros_adjusted_ppg * pr.games_played * 0.6),
            1
        ) as trade_value_score,

        -- Tier for quick comparison
        case
            when pr.current_rank_position <= 6 then 'TIER_1_ELITE'
            when pr.current_rank_position <= 12 then 'TIER_2_WR1_RB1'
            when pr.current_rank_position <= 24 then 'TIER_3_WR2_RB2'
            when pr.current_rank_position <= 36 then 'TIER_4_FLEX'
            else 'TIER_5_BENCH'
        end as trade_value_tier,

        dp.consistency_tier,
        dp.risk_tier,
        ros.projection_confidence

    from player_rankings pr
    left join draft_performance dp on pr.player_id = dp.player_id
    left join ros_rankings ros on pr.player_id = ros.player_id
    where pr.games_played >= 3  -- Only active players
)

select
    player_id,
    player_name,
    position,
    current_rank_position,
    current_vor,
    ros_rank_position,
    ros_adjusted_ppg,
    trade_value_score,
    trade_value_tier,
    consistency_tier,
    risk_tier,
    projection_confidence,

    -- Normalize to 0-100 scale for easier comparison
    round(
        (trade_value_score - min(trade_value_score) over ()) /
        (max(trade_value_score) over () - min(trade_value_score) over ()) * 100,
        1
    ) as trade_value_normalized

from trade_values
order by trade_value_score desc
```

### Phase 2: Dashboard Trade Calculator

Add a new page to the dashboard:

```python
# In dashboard.py, update sidebar navigation (around line 223-231)
page = st.radio(
    "Choose a view:",
    [
        "📊 Standings",
        "🤓 Luck Analysis",
        "📈 Weekly Performance",
        "🎯 Draft Analysis",
        "📈 Rest-of-Season Rankings",
        "⚖️ Trade Analyzer",  # NEW
    ],
)

# Add trade analyzer page (after ROS rankings section)
elif page == "⚖️ Trade Analyzer":
    st.header("⚖️ Trade Analyzer")

    st.markdown("""
    **Evaluate trades using VOR-based value scores.**

    This tool helps determine if a trade is fair by comparing player values.
    Remember: **Context matters!** A fair trade on paper might not fit your team's needs.
    """)

    @st.cache_data
    def load_trade_values(_db_mtime):
        """Load player trade values"""
        try:
            conn = get_db_connection(_db_mtime)
            return conn.execute(
                """
                SELECT
                    player_name,
                    position,
                    current_rank_position as rank,
                    trade_value_score,
                    trade_value_normalized as value,
                    trade_value_tier as tier,
                    risk_tier
                FROM main_analytics.fct_trade_values
                WHERE trade_value_score IS NOT NULL
                ORDER BY trade_value_score DESC
                """
            ).df()
        except Exception as e:
            st.error(f"⚠️ Could not load trade values: {str(e)}")
            return pd.DataFrame()

    trade_values_df = load_trade_values(get_db_mtime())

    if not trade_values_df.empty:
        st.subheader("🔄 Compare Trade")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📤 Team A Gives:**")
            team_a_players = st.multiselect(
                "Select players Team A is trading away:",
                options=trade_values_df["player_name"].tolist(),
                key="team_a"
            )

        with col2:
            st.markdown("**📥 Team B Gives:**")
            team_b_players = st.multiselect(
                "Select players Team B is trading away:",
                options=trade_values_df["player_name"].tolist(),
                key="team_b"
            )

        if team_a_players or team_b_players:
            # Calculate total values
            team_a_value = trade_values_df[
                trade_values_df["player_name"].isin(team_a_players)
            ]["value"].sum()

            team_b_value = trade_values_df[
                trade_values_df["player_name"].isin(team_b_players)
            ]["value"].sum()

            value_diff = abs(team_a_value - team_b_value)

            # Display trade summary
            st.markdown("---")
            st.subheader("📊 Trade Value Summary")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Team A Total Value", f"{team_a_value:.1f}")
            with col2:
                st.metric("Team B Total Value", f"{team_b_value:.1f}")
            with col3:
                winning_team = "Team A" if team_a_value > team_b_value else "Team B"
                st.metric("Value Difference", f"{value_diff:.1f}", delta=f"{winning_team} wins")

            # Trade verdict
            if value_diff < 5:
                verdict = "✅ FAIR TRADE"
                verdict_color = "green"
                explanation = "Values are very close. This is a balanced trade."
            elif value_diff < 15:
                verdict = "⚠️ SLIGHT IMBALANCE"
                verdict_color = "orange"
                explanation = f"{winning_team} gets slightly better value, but could be justified by team needs."
            else:
                verdict = "❌ LOPSIDED"
                verdict_color = "red"
                explanation = f"{winning_team} clearly wins this trade. Reconsider unless there's strong team context."

            st.markdown(f"### {verdict}")
            st.markdown(explanation)

            # Show player details
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Team A Details:**")
                team_a_details = trade_values_df[
                    trade_values_df["player_name"].isin(team_a_players)
                ][["player_name", "position", "rank", "value", "tier", "risk_tier"]]
                st.dataframe(team_a_details, hide_index=True)

            with col2:
                st.markdown("**Team B Details:**")
                team_b_details = trade_values_df[
                    trade_values_df["player_name"].isin(team_b_players)
                ][["player_name", "position", "rank", "value", "tier", "risk_tier"]]
                st.dataframe(team_b_details, hide_index=True)

        # Show full trade value chart
        st.markdown("---")
        st.subheader("📈 Player Trade Values")

        position_filter = st.multiselect(
            "Filter by Position:",
            options=["QB", "RB", "WR", "TE"],
            default=["QB", "RB", "WR", "TE"]
        )

        filtered_trades = trade_values_df[
            trade_values_df["position"].isin(position_filter)
        ]

        st.dataframe(
            filtered_trades,
            use_container_width=True,
            hide_index=True,
            column_config={
                "player_name": "Player",
                "position": "Pos",
                "rank": st.column_config.NumberColumn("Rank"),
                "trade_value_score": st.column_config.NumberColumn(
                    "Raw Value", format="%.1f"
                ),
                "value": st.column_config.ProgressColumn(
                    "Trade Value",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                ),
                "tier": "Tier",
                "risk_tier": "Risk",
            },
        )

        st.markdown("""
        **⚠️ Important Disclaimers:**
        - This is a **starting point** for trade discussions, not absolute truth
        - **Team context matters**: A QB1 is worth less if you already have Mahomes
        - **League scoring**: Values assume standard PPR scoring
        - **Injuries**: Tool doesn't account for breaking injury news
        - **Playoffs**: Playoff schedule strength not included (yet)

        Use this tool + your own judgment!
        """)
```

## Task

1. Create `dbt/models/marts/fct_trade_values.sql`
2. Update `analytics/dashboard.py` to add trade analyzer page
3. Run DBT: `cd dbt && poetry run dbt build --select fct_trade_values`
4. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
5. Navigate to "Trade Analyzer" tab
6. Test a sample trade (e.g., compare Saquon vs CeeDee + Kelce)

## Completion Criteria

- [ ] Trade values model calculates VOR-based scores
- [ ] Dashboard shows interactive trade comparison tool
- [ ] Trade verdict (Fair/Slight Imbalance/Lopsided) is calculated correctly
- [ ] Full trade value chart is displayed
- [ ] All tests pass

## Validation

Test with a known lopsided trade:

- Team A gives: Christian McCaffrey (RB1)
- Team B gives: Random WR3 + QB2

Expected verdict: "LOPSIDED - Team A clearly wins"

---

**Future Enhancements:**

- Roster context (2-for-1 trades hurt depth)
- Playoff schedule adjustment
- Injury risk discount
- Keeper/dynasty value (future picks)

---

**After completing this task:**

1. Mark #15 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 15` (or manually update)
3. Move to prompt #16
