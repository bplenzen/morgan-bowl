"""
🏈 Morgan Bowl Fantasy Football Dashboard
Interactive analytics for league members to explore standings, luck, and performance.

Last updated: 2025-10-28 (Week 8)
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Position color mapping (Sleeper style - light transparent fills)
POSITION_COLORS = {
    "WR": "#E3F2FD",  # Light blue
    "RB": "#E8F5E9",  # Light green
    "QB": "#FFEBEE",  # Light red
    "TE": "#FFF3E0",  # Light orange
    "K": "#F3E5F5",  # Light purple
    "DEF": "#EFEBE9",  # Light brown
}


def style_position_row(row):
    """Apply background color to entire row based on position"""
    position = row.get("position", "")

    # K/DEF: Gray out (streaming positions)
    if position in ("K", "DEF"):
        return ["background-color: #f5f5f5; opacity: 0.6" for _ in row]

    # Regular positions: color by position
    bg_color = POSITION_COLORS.get(position, "white")
    return [f"background-color: {bg_color}" for _ in row]


# VOR Tier color mapping (Boris Chen style)
VOR_TIER_COLORS = {
    "Elite": "#2ecc71",  # Green - top tier
    "High Value": "#3498db",  # Blue - strong value
    "Solid Starter": "#f39c12",  # Orange - solid
    "Depth/Flex": "#95a5a6",  # Gray - depth piece
    "Replacement": "#e74c3c",  # Red - replacement level
    "Bust": "#c0392b",  # Dark red - negative value
}


def get_tier_emoji(tier_label):
    """Add emoji for quick visual scan"""
    tier_emojis = {
        "Elite": "🌟",
        "High Value": "⭐",
        "Solid Starter": "✅",
        "Depth/Flex": "📊",
        "Replacement": "⚠️",
        "Bust": "❌",
    }
    return tier_emojis.get(tier_label, "")


# Page config
st.set_page_config(
    page_title="Morgan Bowl Analytics",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# Database connection
def get_db_path():
    """Get the path to the DuckDB warehouse"""
    return Path(__file__).parent.parent / "data" / "warehouse.duckdb"


def get_db_mtime():
    """Get database file modification time for cache invalidation"""
    db_path = get_db_path()
    if db_path.exists():
        return db_path.stat().st_mtime
    return 0


@st.cache_resource
def get_db_connection(_db_mtime):
    """Connect to DuckDB warehouse

    Args:
        _db_mtime: Database file modification time (used for cache invalidation)
    """
    db_path = get_db_path()
    return duckdb.connect(str(db_path), read_only=True)


@st.cache_data
def load_standings(_db_mtime):
    """Load current standings"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                manager_name,
                wins,
                losses,
                round(win_pct, 3) as win_pct,
                round(points_for, 2) as points_for,
                round(points_against, 2) as points_against,
                round(point_diff, 2) as point_diff
            FROM main_analytics.fct_standings
            ORDER BY wins DESC, points_for DESC
        """
        ).df()
    except Exception as e:
        # Simple error handling: log it and return empty DataFrame
        # This way the app doesn't crash, just shows "no data"
        st.error(f"⚠️ Could not load standings: {str(e)}")
        return pd.DataFrame()


@st.cache_data
def load_weekly_performance(_db_mtime):
    """Load week-by-week performance"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                week,
                manager_name,
                round(points, 2) as points,
                round(opponent_points, 2) as opponent_points,
                opponent_manager_name,
                win_flag
            FROM main_analytics.fct_matchups
            ORDER BY week, points DESC
        """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load weekly performance: {str(e)}")
        return pd.DataFrame()


@st.cache_data
def load_advanced_luck(_db_mtime):
    """Load advanced luck metrics (all-play record, expected wins, schedule strength)"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                manager_name,
                actual_wins,
                actual_losses,
                round(expected_wins, 2) as expected_wins,
                round(wins_over_expected, 2) as wins_over_expected,
                all_play_wins,
                all_play_games,
            round(all_play_win_pct, 3) as all_play_win_pct,
            round(schedule_luck_index, 2) as schedule_luck_index,
            schedule_difficulty,
            close_wins,
            close_losses,
            total_close_games,
            round(close_game_win_pct, 3) as close_game_win_pct,
            round(points_stddev, 2) as points_stddev,
            round(avg_points, 2) as avg_points,
            round(points_range, 2) as points_range,
            round(composite_luck_score, 1) as composite_luck_score,
            luck_rating
        FROM main_analytics.fct_advanced_luck
        ORDER BY composite_luck_score DESC
    """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load advanced luck metrics: {str(e)}")
        return pd.DataFrame()


@st.cache_data
def load_draft_performance(_db_mtime):
    """Load draft analysis with grades and metrics (including NEW uncertainty quantification and spike weeks)"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                dp.pick_no,
                dp.round,
                dp.player_name,
                dp.position,
                dp.current_rank_position,
                dp.manager_name,
                round(dp.value_over_replacement, 1) as vor,
                round(dp.risk_adjusted_scarcity_vor, 1) as adj_vor,
                -- NEW: Uncertainty metrics
                round(dp.risk_adjusted_vor_lower_bound, 1) as vor_lower,
                round(dp.risk_adjusted_vor_upper_bound, 1) as vor_upper,
                round(dp.vor_uncertainty_range, 1) as vor_uncertainty,
                round(dp.grade_score_lower_bound, 1) as grade_lower,
                round(dp.grade_score_upper_bound, 1) as grade_upper,
                round(dp.grade_score_uncertainty, 1) as grade_uncertainty,
                -- NEW: Pick-value curve metrics
                round(dp.expected_vor_at_pick, 1) as expected_vor,
                dp.expected_value_tier,
                round(dp.risk_adjusted_scarcity_vor - dp.expected_vor_at_pick, 1) as value_vs_expected,
                dp.pick_grade,
                dp.grade_score,
                dp.value_verdict,
                dp.consistency_tier,
                dp.risk_tier,
                dp.vor_tier,
                dp.vor_tier_label,
                dp.draft_day_opportunity_cost,
                dp.games_played,
                -- NEW: Spike weeks from variance metrics (JJ Zachariason method)
                wpv.spike_weeks,
                wpv.spike_week_rate_pct as spike_rate,
                wpv.elite_spike_weeks as elite_spikes,
                wpv.spike_tier,
                wpv.championship_upside
            FROM main_analytics.fct_draft_performance dp
            LEFT JOIN main_analytics.int_player_weekly_variance wpv
                ON dp.player_id = wpv.player_id
            ORDER BY dp.pick_no
        """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load draft analysis: {str(e)}")
        return pd.DataFrame()


# Header
st.title("🏈 Morgan Bowl Fantasy Football Analytics")
st.markdown("*Data-driven insights for the most competitive fantasy league*")

# Sidebar
with st.sidebar:
    st.image(
        "https://sleepercdn.com/images/v2/icons/football/nfl_default.png", width=100
    )
    st.markdown("## Navigation")
    page = st.radio(
        "Choose a view:",
        [
            "📊 Standings",
            "🤓 Luck Analysis",
            "📈 Weekly Performance",
            "🎯 Draft Analysis",
            "🔮 Rest-of-Season Rankings",
        ],
    )

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        """
    This dashboard analyzes your fantasy football league using:
    - **Actual Record**: Head-to-head wins/losses
    - **Luck Analysis**: Advanced statistical metrics (all-play record, expected wins, schedule strength)
    - **Weekly Performance**: Scoring trends over time
    """
    )

# Main content
if page == "📊 Standings":
    st.header("Current Standings")

    standings_df = load_standings(get_db_mtime())

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        leader = standings_df.iloc[0]
        st.metric(
            "League Leader",
            leader["manager_name"],
            f"{leader['wins']}-{leader['losses']}",
        )
    with col2:
        highest_scorer = standings_df.nlargest(1, "points_for").iloc[0]
        st.metric(
            "Highest Scorer",
            highest_scorer["manager_name"],
            f"{highest_scorer['points_for']:.1f} pts",
        )
    with col3:
        avg_points = standings_df["points_for"].mean()
        st.metric("Avg Points For", f"{avg_points:.1f}")
    with col4:
        total_weeks = standings_df["wins"].iloc[0] + standings_df["losses"].iloc[0]
        st.metric("Weeks Completed", total_weeks)

    # Standings table
    st.dataframe(
        standings_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "wins": "W",
            "losses": "L",
            "win_pct": st.column_config.NumberColumn("Win %", format="%.3f"),
            "points_for": st.column_config.NumberColumn("PF", format="%.2f"),
            "points_against": st.column_config.NumberColumn("PA", format="%.2f"),
            "point_diff": st.column_config.NumberColumn("+/-", format="%.2f"),
        },
    )

    # Points visualization
    fig = px.bar(
        standings_df.sort_values("points_for", ascending=True),
        x="points_for",
        y="manager_name",
        orientation="h",
        title="Total Points Scored",
        labels={"points_for": "Points", "manager_name": "Manager"},
        color="win_pct",
        color_continuous_scale="RdYlGn",
    )
    st.plotly_chart(fig, use_container_width=True)

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
                "proj_wins": st.column_config.NumberColumn(
                    "Projected Wins", format="%.1f"
                ),
                "playoff_pct": st.column_config.ProgressColumn(
                    "Playoff %",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "playoff_status": "Status",
            },
        )

        st.markdown(
            """
        **Methodology**: Uses team scoring distributions + remaining schedule to estimate playoff odds.
        - **SAFE** (>80%): Very likely to make playoffs
        - **LIKELY** (60-80%): Favored to make playoffs
        - **BUBBLE** (40-60%): Coin flip, must win key games
        - **LONGSHOT** (<40%): Needs help + strong finish
        """
        )

elif page == "🤓 Luck Analysis":
    st.header("🤓 Advanced Luck Analytics")

    # NOTE: This page replaces the old "Justice Rankings" feature (deprecated Oct 2025)
    # Old approach: Simple top-6/bottom-6 median split
    # New approach: All-play record, expected wins, schedule strength, close games
    # The old fct_justice_record model has been removed (deprecated)

    st.markdown(
        """
    **Composite Luck Score Formula:**
    ```
    50 (baseline) +
    (Wins Over Expected × 10) +        [60% weight]
    (Schedule Luck Index × -1.0) +     [35% weight]
    (Close Game Win% - 0.5) × 5        [5% weight]
    ```

    **Key Metrics:**
    - **Expected Wins**: If you played everyone each week, how many total games would you win? That percentage × games played = expected wins.
    - **Wins Over Expected**: Actual wins minus expected wins. The most direct measure of luck.
    - **Schedule Luck Index**: Difference between opponent's actual score and their season average. Positive = you faced tough opponents (unlucky).
    - **Close Games**: Games decided by <5 points. True coin flips with minimal skill influence.
    - **Composite Luck Score**: 0-100 scale combining all factors (50 = average luck).
    """
    )

    advanced_df = load_advanced_luck(get_db_mtime())

    # Top metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        luckiest = advanced_df.iloc[0]
        st.metric(
            "Luckiest (Statistically)",
            luckiest["manager_name"],
            f"{luckiest['composite_luck_score']}/100",
        )
    with col2:
        unluckiest = advanced_df.iloc[-1]
        st.metric(
            "Unluckiest (Statistically)",
            unluckiest["manager_name"],
            f"{unluckiest['composite_luck_score']}/100",
        )
    with col3:
        avg_luck = advanced_df["composite_luck_score"].mean()
        st.metric("League Avg Luck", f"{avg_luck:.1f}/100", "⚖️")

    # Main table
    st.subheader("Advanced Luck Breakdown")

    # Create display record
    advanced_df["actual_record"] = (
        advanced_df["actual_wins"].astype(int).astype(str)
        + "-"
        + advanced_df["actual_losses"].astype(int).astype(str)
    )

    st.dataframe(
        advanced_df[
            [
                "manager_name",
                "actual_record",
                "expected_wins",
                "wins_over_expected",
                "schedule_luck_index",
                "schedule_difficulty",
                "close_game_win_pct",
                "total_close_games",
                "composite_luck_score",
                "luck_rating",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=550,  # Show all 12 teams without scrolling
        column_config={
            "manager_name": "Manager",
            "actual_record": "Actual Record",
            "expected_wins": st.column_config.NumberColumn(
                "Exp Wins", help="Based on all-play win percentage", format="%.2f"
            ),
            "wins_over_expected": st.column_config.NumberColumn(
                "WOE",
                help="Wins Over Expected (60% weight in composite)",
                format="%.2f",
            ),
            "schedule_luck_index": st.column_config.NumberColumn(
                "Sched Luck",
                help="Schedule Luck Index (35% weight). Positive = unlucky, negative = lucky",
                format="%.2f",
            ),
            "schedule_difficulty": st.column_config.TextColumn(
                "Schedule",
                help="Schedule difficulty rating",
            ),
            "close_game_win_pct": st.column_config.NumberColumn(
                "Close Win %",
                help="Win % in games decided by <5 pts (5% weight)",
                format="%.3f",
            ),
            "total_close_games": st.column_config.NumberColumn(
                "Close Games",
                help="Number of games decided by <5 points",
            ),
            "composite_luck_score": st.column_config.ProgressColumn(
                "Composite Score",
                help="0-100 scale combining all factors (50 = average)",
                format="%.1f",
                min_value=0,
                max_value=100,
            ),
            "luck_rating": "Rating",
        },
    )

    # Expandable sections for nerds who want MORE detail
    with st.expander("📊 All-Play Record Details"):
        st.markdown(
            "**What is All-Play Record?** If you played every team in the league each week, this is how you'd perform."
        )
        all_play_sorted = advanced_df.sort_values("all_play_win_pct", ascending=False)
        st.dataframe(
            all_play_sorted[
                ["manager_name", "all_play_wins", "all_play_games", "all_play_win_pct"]
            ],
            use_container_width=True,
            hide_index=True,
            height=550,  # Show all teams
            column_config={
                "manager_name": "Manager",
                "all_play_wins": st.column_config.NumberColumn(
                    "All-Play Wins", help="Total wins if you played everyone"
                ),
                "all_play_games": st.column_config.NumberColumn(
                    "All-Play Games", help="Total possible matchups"
                ),
                "all_play_win_pct": st.column_config.NumberColumn(
                    "All-Play Win %", format="%.3f"
                ),
            },
        )

    with st.expander("📅 Schedule Luck Analysis"):
        st.markdown(
            "**Schedule Luck**: Positive numbers = you faced opponents on their good weeks (unlucky), negative = faced them on bad weeks (lucky)"
        )
        schedule_sorted = advanced_df.sort_values(
            "schedule_luck_index", ascending=False
        )
        st.dataframe(
            schedule_sorted[
                ["manager_name", "schedule_luck_index", "schedule_difficulty"]
            ],
            use_container_width=True,
            hide_index=True,
            height=550,  # Show all teams
            column_config={
                "manager_name": "Manager",
                "schedule_luck_index": st.column_config.NumberColumn(
                    "Schedule Index", help="Higher = tougher opponents", format="%.2f"
                ),
                "schedule_difficulty": "Difficulty Rating",
            },
        )

    with st.expander("🎲 Close Game Performance"):
        st.markdown(
            "**Close Games**: Games decided by <5 points. True coin flips where luck dominates over skill."
        )
        close_df = advanced_df[advanced_df["total_close_games"] > 0].copy()
        close_df["close_record"] = (
            close_df["close_wins"].astype(int).astype(str)
            + "-"
            + close_df["close_losses"].astype(int).astype(str)
        )
        close_sorted = close_df.sort_values(
            "close_game_win_pct", ascending=False, na_position="last"
        )
        st.dataframe(
            close_sorted[
                [
                    "manager_name",
                    "close_record",
                    "total_close_games",
                    "close_game_win_pct",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            height=550,  # Show all teams
            column_config={
                "manager_name": "Manager",
                "close_record": "Close Game Record",
                "total_close_games": "Total Close Games",
                "close_game_win_pct": st.column_config.NumberColumn(
                    "Close Game Win %", format="%.3f"
                ),
            },
        )

    with st.expander("📉 Consistency Metrics"):
        st.markdown("**Consistency**: How much do your scores vary week-to-week?")
        consistency_sorted = advanced_df.sort_values("points_stddev", ascending=True)
        st.dataframe(
            consistency_sorted[
                ["manager_name", "avg_points", "points_stddev", "points_range"]
            ],
            use_container_width=True,
            hide_index=True,
            height=550,  # Show all teams
            column_config={
                "manager_name": "Manager",
                "avg_points": st.column_config.NumberColumn(
                    "Avg Points", format="%.2f"
                ),
                "points_stddev": st.column_config.NumberColumn(
                    "Std Deviation", help="Lower = more consistent", format="%.2f"
                ),
                "points_range": st.column_config.NumberColumn(
                    "Range (Max-Min)",
                    help="Difference between best and worst week",
                    format="%.2f",
                ),
            },
        )

    # Visualization: Composite Luck Score
    st.subheader("Composite Luck Score Distribution")

    fig = go.Figure()

    # Color by luck level
    colors = []
    for score in advanced_df["composite_luck_score"]:
        if score >= 65:
            colors.append("#2ecc71")  # Very lucky - green
        elif score >= 55:
            colors.append("#a8e6cf")  # Lucky - light green
        elif score >= 45:
            colors.append("#95a5a6")  # Fair - gray
        elif score >= 35:
            colors.append("#f39c12")  # Unlucky - orange
        else:
            colors.append("#e74c3c")  # Very unlucky - red

    fig.add_trace(
        go.Bar(
            x=advanced_df["manager_name"],
            y=advanced_df["composite_luck_score"],
            marker_color=colors,
            text=advanced_df["composite_luck_score"],
            textposition="outside",
            name="Luck Score",
        )
    )

    # Add reference line at 50 (average)
    fig.add_hline(
        y=50, line_dash="dash", line_color="black", annotation_text="Average (50)"
    )

    fig.update_layout(
        title="Composite Luck Score (0-100 scale)",
        xaxis_title="Manager",
        yaxis_title="Luck Score",
        yaxis_range=[0, 100],
        showlegend=False,
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown(
        "*🤓 Methodology: Combines all-play record (60%), schedule strength (35%), and close game performance (5%) into a single composite score.*"
    )

elif page == "📈 Weekly Performance":
    st.header("Week-by-Week Performance")

    weekly_df = load_weekly_performance(get_db_mtime())

    # Week selector
    weeks = sorted(weekly_df["week"].unique())
    selected_week = st.selectbox("Select Week", weeks, index=len(weeks) - 1)

    week_data = weekly_df[weekly_df["week"] == selected_week].copy()
    week_data["result"] = week_data["win_flag"].map({1: "✅ Win", 0: "❌ Loss"})

    # Week summary
    col1, col2, col3 = st.columns(3)
    with col1:
        highest = week_data.nlargest(1, "points").iloc[0]
        st.metric(
            "Highest Score", highest["manager_name"], f"{highest['points']:.2f} pts"
        )
    with col2:
        lowest = week_data.nsmallest(1, "points").iloc[0]
        st.metric("Lowest Score", lowest["manager_name"], f"{lowest['points']:.2f} pts")
    with col3:
        avg_score = week_data["points"].mean()
        st.metric("Average Score", f"{avg_score:.2f} pts")

    # Matchup results
    st.subheader(f"Week {selected_week} Matchups")
    st.dataframe(
        week_data[
            [
                "manager_name",
                "points",
                "opponent_manager_name",
                "opponent_points",
                "result",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "points": st.column_config.NumberColumn("Score", format="%.2f"),
            "opponent_manager_name": "Opponent",
            "opponent_points": st.column_config.NumberColumn(
                "Opp Score", format="%.2f"
            ),
            "result": "Result",
        },
    )

    # Weekly scoring trends
    st.subheader("Scoring Trends Across All Weeks")
    manager = st.selectbox("Select Manager", sorted(weekly_df["manager_name"].unique()))

    manager_data = weekly_df[weekly_df["manager_name"] == manager].sort_values("week")

    # Calculate league average per week
    league_avg = weekly_df.groupby("week")["points"].mean().reset_index()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=manager_data["week"],
            y=manager_data["points"],
            mode="lines+markers",
            name="Points Scored",
            line=dict(color="blue", width=3),
            marker=dict(size=10),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=manager_data["week"],
            y=manager_data["opponent_points"],
            mode="lines+markers",
            name="Opponent Points",
            line=dict(color="red", width=2, dash="dash"),
            marker=dict(size=8),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=league_avg["week"],
            y=league_avg["points"],
            mode="lines",
            name="League Average",
            line=dict(color="green", width=2, dash="dot"),
            opacity=0.7,
        )
    )

    fig.update_layout(
        title=f"{manager} - Weekly Scoring",
        xaxis_title="Week",
        yaxis_title="Points",
        height=400,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

elif page == "🎯 Draft Analysis":
    st.header("🎯 Draft Performance Analysis")

    st.markdown(
        """
    **How we grade your draft picks:**
    - 🎯 **Did you get good value?** - Compare each pick to what you could've gotten
    - 📊 **How risky is the player?** - Injuries and inconsistency lower the grade
    - 🏈 **Position scarcity matters** - Elite RBs/TEs are worth more than WRs/QBs
    - ✅ **Confidence ranges** - Shows if a grade is "solid A" or "risky A with boom/bust potential"
    """
    )

    st.info(
        """
        **📌 Note on Draft Grades & Trades:**
        Draft grades reflect the quality of the **original draft decision** made by the drafter.
        If a player was later traded to another team, the grade still applies to the manager who
        drafted them, not the current owner. This evaluates the *draft-day decision quality*,
        separate from trade outcomes.
        """
    )

    with st.expander("📖 How does this actually work? (Click to learn more)"):
        st.markdown(
            """
            ### 🎯 Value Over Replacement (VOR)

            **What it is:** How many more points a player scores compared to a "replacement level" player
            (the worst starter you'd consider).

            **Example:** If Saquon Barkley averages 18 PPG and the worst startable RB (RB28) averages 10 PPG,
            Saquon's VOR = (18 - 10) × games played. The bigger the gap, the more valuable.

            **Why it matters:** Not all 18 PPG players are equal! A QB averaging 18 PPG is bad (you can stream),
            but an RB averaging 18 PPG is elite (RBs are scarce).

            ---

            ### 🎲 Risk-Adjusted Metrics

            **What it is:** We penalize players who:
            - **Miss games** (injuries, suspensions)
            - **Have inconsistent scoring** (boom 30 one week, bust 5 the next)
            - **Play injury-prone positions** (RBs get hurt more than QBs)

            **Example:** Two RBs with 15 PPG:
            - **Player A:** Played all 8 games, scores 13-17 every week → Low risk, reliable
            - **Player B:** Missed 3 games, scores 5-25 → High risk, unreliable

            Player A gets a higher grade because you can actually *start* them with confidence.

            ---

            ### 🏈 Positional Scarcity

            **What it is:** Some positions have a huge gap between elite and replacement, others don't.

            **The scarcity rankings:**
            - **Tight End (×1.30):** MASSIVE gap. Kelce/Bowers vs TE12 is huge.
            - **Running Back (×1.20):** Large gap. Elite RBs are rare and valuable.
            - **Wide Receiver (×1.05):** Moderate gap. Lots of startable WRs available.
            - **Quarterback (×1.00):** Small gap. Even QB15 can have big weeks.

            **Why it matters:** Drafting Brock Bowers (TE1) in Round 2 looks weird but the scarcity
            makes it smart. Meanwhile, drafting Patrick Mahomes in Round 3 is a reach because
            you can get similar production from a Round 10 QB.

            ---

            ### 💰 Draft-Day Opportunity Cost

            **What it is:** Who was still on the board that you *should've* taken?

            **Example:** You draft a WR ranked 60th overall at pick 30. But a WR ranked 40th was
            still available and got picked 5 picks later. You "reached" by ~20 spots.

            **Why it matters:** Separates smart value picks from reaches. Even if your reach worked out
            (he went off!), the process was still questionable.

            ---

            ### 📊 Confidence Ranges (± Grades)

            **What it is:** How sure are we about this grade? Is it a "lock" or could it change?

            **Example:**
            - **Player A:** Grade 85 ± 5 → Very confident, consistent performer
            - **Player B:** Grade 85 ± 25 → Boom/bust player, grade could be 60 or 110 depending on week

            **Why it matters:** Helps you understand *how* your picks succeeded/failed. Did you draft
            a safe, reliable RB2 (narrow range) or a volatile lottery ticket (wide range)?

            ---

            ### 📉 Pick-Value Curve

            **What it is:** What VOR was *expected* at each draft pick, based on expert consensus (ADP)?

            **Example:** Pick #10 historically produces ~75 VOR. If your pick #10 produced 95 VOR,
            that's a **+20 steal**. If it produced 50 VOR, that's a **-25 bust**.

            **Why it matters:** Separates lucky late-round gems from early-round disasters.
            Getting 50 VOR from pick #100 = amazing! Getting 50 VOR from pick #10 = disaster.

            ---

            ### 🤔 Why grade draft *decisions* separately from *outcomes*?

            **Good process can have bad outcomes** (injuries, bad luck):
            - Draft Christian McCaffrey #1 overall → Smart decision ✅
            - He tears ACL Week 2 → Bad outcome ❌
            - **Grade:** Still an A for the decision, because you couldn't predict the injury

            **Bad process can have good outcomes** (getting lucky):
            - Reach for a QB in Round 3 when better RBs available → Bad decision ❌
            - That QB goes off and finishes QB1 → Good outcome ✅
            - **Grade:** Still a C/D for the decision, because you got lucky with a reach

            This system grades your **decision-making** (did you draft smart?), not just your
            **results** (did your players stay healthy?). Over many drafts, good process wins.
            """
        )

    draft_df = load_draft_performance(get_db_mtime())

    if draft_df.empty:
        st.warning("No draft data available")
    else:
        # Manager filter
        managers = ["All"] + sorted(draft_df["manager_name"].unique().tolist())
        selected_manager = st.selectbox("Filter by Manager:", managers)

        filtered_df = (
            draft_df
            if selected_manager == "All"
            else draft_df[draft_df["manager_name"] == selected_manager]
        )

        # Grade distribution metrics (ENHANCED with uncertainty)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_grade = filtered_df["grade_score"].mean()
            avg_uncertainty = filtered_df["grade_uncertainty"].mean()
            st.metric(
                "Average Grade Score",
                f"{avg_grade:.1f}",
                delta=f"±{avg_uncertainty:.1f}" if pd.notna(avg_uncertainty) else None,
                delta_color="off",
            )
        with col2:
            a_grades = len(filtered_df[filtered_df["grade_score"] >= 90])
            st.metric("A Grades", a_grades)
        with col3:
            f_grades = len(filtered_df[filtered_df["grade_score"] < 30])
            st.metric("F Grades", f_grades)
        with col4:
            # NEW: Show steals vs reaches
            steals = len(filtered_df[filtered_df["value_vs_expected"] > 20])
            reaches = len(filtered_df[filtered_df["value_vs_expected"] < -20])
            st.metric("Steals / Reaches", f"{steals} / {reaches}")

        # ========== SECTION 1: DRAFT BOARD ==========
        st.markdown("---")
        st.subheader("📋 All Draft Picks")

        # Add uncertainty toggle (default OFF for simplicity)
        show_uncertainty = st.checkbox(
            "Show Advanced Stats (VOR, Uncertainty)", value=False
        )

        # Create draft pick notation (e.g., 1.01, 2.12)
        filtered_df = filtered_df.copy()
        filtered_df["draft_pick"] = filtered_df.apply(
            lambda row: f"{row['round']}.{((row['pick_no'] - 1) % 12) + 1:02d}",
            axis=1,
        )

        # Format position with inline rank (e.g., WR3, RB12)
        def format_position_with_rank(row):
            """Format position with inline rank, handling edge cases"""
            position = row["position"]
            rank = row["current_rank_position"]
            games_played = row["games_played"]

            # K/DEF: No ranking (streaming positions)
            if position in ("K", "DEF"):
                return position

            # Inactive players or missing rank data
            if games_played == 0 or pd.isna(rank):
                return f"{position}(NR)"

            # Standard format: WR3, RB12, etc.
            return f"{position}{int(rank)}"

        filtered_df["position_display"] = filtered_df.apply(
            format_position_with_rank, axis=1
        )

        # Replace NULL pick_grades with explanation for K/DEF (streaming positions)
        filtered_df["pick_grade"] = filtered_df.apply(
            lambda row: (
                "N/A (Streaming)"
                if row["position"] in ["K", "DEF"]
                else row["pick_grade"]
            ),
            axis=1,
        )

        # Simple view: Just the essentials
        # Note: Keep "position" for styling, display "position_display" to user
        display_cols = [
            "draft_pick",
            "player_name",
            "position",
            "position_display",
            "manager_name",
            "vor_tier_label",  # NEW: Boris Chen style tier
            "pick_grade",
            "value_verdict",
        ]

        # Advanced view: Add technical stats
        if show_uncertainty:
            display_cols.insert(
                6, "adj_vor"
            )  # After vor_tier_label (adjusted for extra col)
            display_cols.insert(7, "vor_uncertainty")  # After adj_vor
            display_cols.insert(9, "grade_uncertainty")  # After pick_grade

        # Apply position-based row coloring
        styled_df = filtered_df[display_cols].style.apply(style_position_row, axis=1)

        # Column configuration (only used if columns are displayed)
        column_config = {
            "draft_pick": "Pick",
            "player_name": "Player",
            "position": None,  # Hide raw position column
            "position_display": st.column_config.TextColumn(
                "Pos",
                help="K/DEF are streaming positions and not graded for draft value",
            ),
            "manager_name": "Manager",
            "vor_tier_label": st.column_config.TextColumn(
                "Tier",
                help="Boris Chen style value tier (Elite > High > Solid > Depth > Replacement)",
            ),
            "pick_grade": st.column_config.TextColumn(
                "Grade", help="Letter grade based on VOR. K/DEF not graded (streaming)"
            ),
            "value_verdict": "Verdict",
        }

        # Add advanced column configs only if showing them
        if show_uncertainty:
            column_config["adj_vor"] = st.column_config.NumberColumn(
                "Adj VOR", format="%.1f", help="Value Over Replacement (risk-adjusted)"
            )
            column_config["vor_uncertainty"] = st.column_config.NumberColumn(
                "VOR ±",
                format="%.1f",
                help="Uncertainty range (wider = more volatile)",
            )
            column_config["grade_uncertainty"] = st.column_config.NumberColumn(
                "Grade ±", format="%.1f", help="Grade uncertainty"
            )

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
        )

        # Best/Worst picks
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏆 Best Picks")
            best = filtered_df.nlargest(5, "grade_score")
            best_cols = [
                "draft_pick",
                "player_name",
                "position",
                "position_display",
                "pick_grade",
                "adj_vor",
                "grade_uncertainty",
            ]
            st.dataframe(
                best[best_cols].style.apply(style_position_row, axis=1),
                hide_index=True,
                column_config={
                    "draft_pick": "Pick",
                    "player_name": "Player",
                    "position": None,  # Hide for styling
                    "position_display": "Pos",  # Show formatted
                    "pick_grade": "Grade",
                    "adj_vor": st.column_config.NumberColumn("Adj VOR", format="%.1f"),
                    "grade_uncertainty": st.column_config.NumberColumn(
                        "±", format="%.1f"
                    ),
                },
            )

        with col2:
            st.subheader("💔 Worst Picks")
            worst = filtered_df[filtered_df["round"] <= 10].nsmallest(5, "grade_score")
            worst_cols = [
                "draft_pick",
                "player_name",
                "position",
                "position_display",
                "pick_grade",
                "adj_vor",
                "grade_uncertainty",
            ]
            st.dataframe(
                worst[worst_cols].style.apply(style_position_row, axis=1),
                hide_index=True,
                column_config={
                    "draft_pick": "Pick",
                    "player_name": "Player",
                    "position": None,  # Hide for styling
                    "position_display": "Pos",  # Show formatted
                    "pick_grade": "Grade",
                    "adj_vor": st.column_config.NumberColumn("Adj VOR", format="%.1f"),
                    "grade_uncertainty": st.column_config.NumberColumn(
                        "±", format="%.1f"
                    ),
                },
            )

        # ========== SECTION 2: UNCERTAINTY ANALYSIS ==========
        st.markdown("---")
        st.subheader("📊 Confidence Interval Analysis")

        # Calculate dynamic threshold
        weeks_completed = (
            filtered_df["games_played"].max() if not filtered_df.empty else 8
        )
        MIN_AVAILABILITY_PCT = 0.60
        min_games_threshold = max(5, int(weeks_completed * MIN_AVAILABILITY_PCT))

        st.markdown(
            f"""
        **Understanding Uncertainty:**
        - **Wide confidence intervals** = High volatility, boom-or-bust player
        - **Narrow confidence intervals** = Consistent, reliable floor
        - Uncertainty decreases as season progresses (more data)
        - *Showing players with ≥{min_games_threshold} games for reliable estimates (minimum {int(MIN_AVAILABILITY_PCT*100)}% availability through Week {weeks_completed})*
        """
        )

        # Filter to players with uncertainty data AND sufficient sample size (calculated above)
        with_uncertainty = filtered_df[
            (filtered_df["vor_uncertainty"].notna())
            & (filtered_df["games_played"] >= min_games_threshold)
        ].copy()

        if not with_uncertainty.empty:
            # VOR confidence interval chart (top 30 picks)
            top_picks = with_uncertainty[with_uncertainty["pick_no"] <= 30].copy()

            if not top_picks.empty:
                fig = go.Figure()

                for _, row in top_picks.iterrows():
                    # Error bar
                    fig.add_trace(
                        go.Scatter(
                            x=[row["pick_no"]],
                            y=[row["adj_vor"]],
                            error_y=dict(
                                type="data",
                                symmetric=False,
                                array=(
                                    [row["vor_upper"] - row["adj_vor"]]
                                    if pd.notna(row["vor_upper"])
                                    else [0]
                                ),
                                arrayminus=(
                                    [row["adj_vor"] - row["vor_lower"]]
                                    if pd.notna(row["vor_lower"])
                                    else [0]
                                ),
                                color="lightblue",
                                thickness=2,
                                width=4,
                            ),
                            mode="markers",
                            marker=dict(size=10, color="#448AFF"),
                            name=row["player_name"],
                            hovertemplate=f"<b>{row['player_name']}</b><br>"
                            + f"Pick #{row['pick_no']}<br>"
                            + f"VOR: {row['adj_vor']:.1f}<br>"
                            + f"Range: {row['vor_lower']:.1f} - {row['vor_upper']:.1f}<br>"
                            + f"Uncertainty: ±{row['vor_uncertainty']/2:.1f}<extra></extra>",
                            showlegend=False,
                        )
                    )

                fig.update_layout(
                    title="VOR Confidence Intervals (Top 30 Picks)",
                    xaxis_title="Draft Pick Number",
                    yaxis_title="Risk-Adjusted VOR",
                    height=500,
                    template="plotly_white",
                    hovermode="closest",
                )

                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "📊 Uncertainty data will appear after Week 5 (need 5+ games for reliable variance estimates)"
            )

        # ========== SECTION 3: VALUE CURVE ANALYSIS ==========
        st.markdown("---")
        st.subheader("📉 Pick-Value Curve Analysis")

        st.markdown(
            """
        **Value vs Expected:**
        - Shows how each pick performed vs expected value at that draft position
        - **Positive = Steal** (exceeded expectations - great outcome)
        - **Negative = Disappointment** (fell short of expectations - injury, underperformance, etc.)
        - *Note: This measures outcomes, not draft decisions. Injured players show as disappointments even if the pick made sense.*
        """
        )

        # Value vs Expected scatter plot
        active_picks = filtered_df[filtered_df["games_played"] > 0].copy()

        if not active_picks.empty and "value_vs_expected" in active_picks.columns:
            fig = px.scatter(
                active_picks,
                x="expected_vor",
                y="adj_vor",
                color="position",
                hover_data=["player_name", "pick_no", "value_vs_expected"],
                title="Actual VOR vs Expected VOR (Picks Above Line = Outperformers)",
                labels={
                    "expected_vor": "Expected VOR at Pick",
                    "adj_vor": "Actual VOR",
                },
                color_discrete_map={
                    "QB": "#FF6B6B",
                    "RB": "#4ECDC4",
                    "WR": "#45B7D1",
                    "TE": "#FFA07A",
                },
            )

            # Add diagonal line (perfect match)
            max_vor = max(
                active_picks["expected_vor"].max(), active_picks["adj_vor"].max()
            )
            fig.add_trace(
                go.Scatter(
                    x=[0, max_vor],
                    y=[0, max_vor],
                    mode="lines",
                    line=dict(color="gray", dash="dash"),
                    name="Perfect Match",
                    showlegend=True,
                )
            )

            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

            # Biggest steals and reaches
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💎 Biggest Steals")
                steals = active_picks.nlargest(5, "value_vs_expected")
                steals_cols = [
                    "draft_pick",
                    "player_name",
                    "position",
                    "position_display",
                    "expected_vor",
                    "adj_vor",
                    "value_vs_expected",
                ]
                st.dataframe(
                    steals[steals_cols].style.apply(style_position_row, axis=1),
                    hide_index=True,
                    column_config={
                        "draft_pick": "Pick",
                        "player_name": "Player",
                        "position": None,  # Hide for styling
                        "position_display": "Pos",  # Show formatted
                        "expected_vor": st.column_config.NumberColumn(
                            "Expected", format="%.1f"
                        ),
                        "adj_vor": st.column_config.NumberColumn(
                            "Actual", format="%.1f"
                        ),
                        "value_vs_expected": st.column_config.NumberColumn(
                            "Surplus", format="%.1f"
                        ),
                    },
                )

            with col2:
                st.subheader("💔 Biggest Disappointments")
                reaches = active_picks.nsmallest(5, "value_vs_expected")
                reaches_cols = [
                    "draft_pick",
                    "player_name",
                    "position",
                    "position_display",
                    "expected_vor",
                    "adj_vor",
                    "value_vs_expected",
                ]
                st.dataframe(
                    reaches[reaches_cols].style.apply(style_position_row, axis=1),
                    hide_index=True,
                    column_config={
                        "draft_pick": "Pick",
                        "player_name": "Player",
                        "position": None,  # Hide for styling
                        "position_display": "Pos",  # Show formatted
                        "expected_vor": st.column_config.NumberColumn(
                            "Expected", format="%.1f"
                        ),
                        "adj_vor": st.column_config.NumberColumn(
                            "Actual", format="%.1f"
                        ),
                        "value_vs_expected": st.column_config.NumberColumn(
                            "Shortfall", format="%.1f"
                        ),
                    },
                )
        else:
            st.info("📊 Value curve data available for active players only")

        # ========== SECTION 4: GRADE SUMMARY ==========
        st.markdown("---")

        # Grade distribution chart
        st.subheader("Grade Distribution")
        grade_counts = filtered_df["pick_grade"].str[:1].value_counts().sort_index()
        fig = px.bar(
            x=grade_counts.index,
            y=grade_counts.values,
            labels={"x": "Grade", "y": "Count"},
            title="Draft Grades by Letter",
            color=grade_counts.index,
            color_discrete_map={
                "A": "#2ecc71",
                "B": "#a8e6cf",
                "C": "#95a5a6",
                "D": "#f39c12",
                "F": "#e74c3c",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

        # Value Tier distribution chart (Boris Chen style)
        st.subheader("Value Tier Distribution")
        tier_counts = filtered_df[filtered_df["vor_tier_label"].notna()][
            "vor_tier_label"
        ].value_counts()
        tier_order = [
            "Elite",
            "High Value",
            "Solid Starter",
            "Depth/Flex",
            "Replacement",
            "Bust",
        ]
        tier_counts = tier_counts.reindex(tier_order, fill_value=0)

        fig_tier = px.bar(
            x=tier_counts.index,
            y=tier_counts.values,
            labels={"x": "Tier", "y": "Count"},
            title="Draft Picks by VOR Tier (Boris Chen Style)",
            color=tier_counts.index,
            color_discrete_map=VOR_TIER_COLORS,
        )
        st.plotly_chart(fig_tier, use_container_width=True)

        # Expandable detailed metrics
        with st.expander("📊 Advanced Metrics Breakdown"):
            st.markdown(
                "**Risk Tiers**: How reliable is this player? (Elite/Stable/Moderate/Volatile)"
            )
            st.dataframe(
                filtered_df[
                    [
                        "player_name",
                        "position_display",
                        "vor",
                        "adj_vor",
                        "consistency_tier",
                        "risk_tier",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "player_name": "Player",
                    "position_display": "Pos",
                    "vor": st.column_config.NumberColumn("Raw VOR", format="%.1f"),
                    "adj_vor": st.column_config.NumberColumn(
                        "Risk-Adjusted VOR", format="%.1f"
                    ),
                    "consistency_tier": "Consistency",
                    "risk_tier": "Risk",
                },
            )

        with st.expander("💰 Opportunity Cost Analysis"):
            st.markdown(
                "**What did you pass up?** Shows the best available player at each draft position."
            )
            st.dataframe(
                filtered_df[
                    [
                        "pick_no",
                        "player_name",
                        "adj_vor",
                        "draft_day_opportunity_cost",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "pick_no": "Pick",
                    "player_name": "Drafted",
                    "adj_vor": st.column_config.NumberColumn("Your VOR", format="%.1f"),
                    "draft_day_opportunity_cost": "Best Available (Passed)",
                },
            )

        with st.expander("🔥 Spike Weeks Analysis (Championship Upside)"):
            st.markdown(
                """
                **Spike Weeks**: Games where a player finished **top-12 at their position** (WR1/RB1 performances).

                Research by **JJ Zachariason** (Late Round Podcast) shows spike weeks predict playoff success
                better than average PPG. A boom-bust WR averaging 12 PPG with 4 spike weeks can win championships
                despite a mediocre season average.

                **Why it matters**: Elite weekly performances matter more in playoffs than consistent mediocrity.
                """
            )

            # Filter for players with meaningful games played
            spike_df = filtered_df[
                (filtered_df["games_played"] >= 5)
                & (filtered_df["spike_weeks"].notna())
            ].sort_values("spike_weeks", ascending=False)

            if spike_df.empty:
                st.info("No spike weeks data available for the selected filters.")
            else:
                st.dataframe(
                    spike_df[
                        [
                            "player_name",
                            "position_display",
                            "games_played",
                            "spike_weeks",
                            "spike_rate",
                            "elite_spikes",
                            "spike_tier",
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
                        "spike_tier": st.column_config.TextColumn(
                            "Spike Tier",
                            help="ELITE_SPIKER (50%+) → LOW_SPIKE (<10%)",
                        ),
                        "adj_vor": st.column_config.NumberColumn("VOR", format="%.1f"),
                    },
                )

                # Show championship upside flags
                championship_players = spike_df[spike_df["championship_upside"]]
                if not championship_players.empty:
                    st.success(
                        f"🏆 **Championship Upside Players** (3+ elite spikes): "
                        f"{', '.join(championship_players['player_name'].tolist())}"
                    )

        st.markdown("---")
        st.markdown(
            "*🎓 Methodology: Combines historical performance, consistency metrics, injury risk, and positional scarcity. See docs/DRAFT_ANALYSIS_METHODOLOGY.md for details.*"
        )

elif page == "🔮 Rest-of-Season Rankings":
    st.header("🔮 Rest-of-Season (ROS) Projections")

    st.markdown(
        """
    **ROS rankings weight recent performance more heavily** and adjust for availability.
    Use these for trade decisions and rest-of-season lineup planning.

    - **Trending Up 🔥**: ROS rank >> Season rank (buy low candidate)
    - **Trending Down ❄️**: ROS rank << Season rank (sell high candidate)
    """
    )

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
            lambda x: (
                "🔥 Trending Up"
                if x < -5
                else ("❄️ Trending Down" if x > 5 else "➡️ Steady")
            )
        )

        # Display table
        st.dataframe(
            ros_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "player_name": "Player",
                "position": "Pos",
                "season_rank": st.column_config.NumberColumn("Season Rank"),
                "ros_rank": st.column_config.NumberColumn("ROS Rank"),
                "rank_change": st.column_config.NumberColumn(
                    "Change",
                    help="Negative = trending up, Positive = trending down",
                    format="%+d",
                ),
                "season_ppg": st.column_config.NumberColumn(
                    "Season PPG", format="%.1f"
                ),
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
                risers[
                    [
                        "player_name",
                        "position",
                        "season_rank",
                        "ros_rank",
                        "rank_change",
                    ]
                ],
                hide_index=True,
            )

        with col2:
            st.subheader("❄️ Biggest Fallers (Sell High)")
            fallers = ros_df.nlargest(10, "rank_change")
            st.dataframe(
                fallers[
                    [
                        "player_name",
                        "position",
                        "season_rank",
                        "ros_rank",
                        "rank_change",
                    ]
                ],
                hide_index=True,
            )

        st.markdown("---")
        st.markdown(
            """
        **Methodology:**
        - Uses exponentially weighted moving average (EWMA) to emphasize recent games
        - Last 6 weeks weighted most heavily (recent weeks = 2× → 8× weight)
        - Availability discount for missed games (injury/bye concerns)
        - Minimum 3 games required for projection

        **How to use:**
        - Players trending up may have recovered from injury or increased role
        - Players trending down may be dealing with injuries or declining usage
        - Use with trade analyzer to identify buy-low / sell-high opportunities
        """
        )
    else:
        st.info("ROS rankings will be available after Week 6 (need 3+ recent games)")

# Footer
st.markdown("---")
st.markdown(
    "*Data updated weekly via automated GitLab CI/CD pipeline • Built with Streamlit & DuckDB*"
)
