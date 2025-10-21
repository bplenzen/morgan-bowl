"""
🏈 Morgan Bowl Fantasy Football Dashboard
Interactive analytics for league members to explore standings, luck, and performance.

Last updated: 2025-10-21 (Week 7)
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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
@st.cache_resource
def get_db_connection():
    """Connect to DuckDB warehouse"""
    db_path = Path(__file__).parent.parent / "data" / "warehouse.duckdb"
    return duckdb.connect(str(db_path), read_only=True)


@st.cache_data
def load_standings():
    """Load current standings"""
    try:
        conn = get_db_connection()
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
def load_weekly_performance():
    """Load week-by-week performance"""
    try:
        conn = get_db_connection()
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
def load_advanced_luck():
    """Load advanced luck metrics (all-play record, expected wins, schedule strength)"""
    try:
        conn = get_db_connection()
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
def load_draft_performance():
    """Load draft analysis with grades and metrics (including NEW uncertainty quantification)"""
    try:
        conn = get_db_connection()
        return conn.execute(
            """
            SELECT
                pick_no,
                round,
                player_name,
                position,
                manager_name,
                round(value_over_replacement, 1) as vor,
                round(risk_adjusted_scarcity_vor, 1) as adj_vor,
                -- NEW: Uncertainty metrics
                round(risk_adjusted_vor_lower_bound, 1) as vor_lower,
                round(risk_adjusted_vor_upper_bound, 1) as vor_upper,
                round(vor_uncertainty_range, 1) as vor_uncertainty,
                round(grade_score_lower_bound, 1) as grade_lower,
                round(grade_score_upper_bound, 1) as grade_upper,
                round(grade_score_uncertainty, 1) as grade_uncertainty,
                -- NEW: Pick-value curve metrics
                round(expected_vor_at_pick, 1) as expected_vor,
                expected_value_tier,
                round(risk_adjusted_scarcity_vor - expected_vor_at_pick, 1) as value_vs_expected,
                pick_grade,
                grade_score,
                value_verdict,
                consistency_tier,
                risk_tier,
                draft_day_opportunity_cost,
                games_played
            FROM main_analytics.fct_draft_performance
            ORDER BY pick_no
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
            "🔥 Power Rankings",
            "🎯 Draft Analysis",
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
    - **Power Rankings**: Combined performance metrics
    """
    )

# Main content
if page == "📊 Standings":
    st.header("Current Standings")

    standings_df = load_standings()

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
    (Schedule Luck Index × -0.5) +     [20% weight]
    (Close Game Win% - 0.5) × 20       [20% weight]
    ```

    **Key Metrics:**
    - **Expected Wins**: If you played everyone each week, how many total games would you win? That percentage × games played = expected wins.
    - **Wins Over Expected**: Actual wins minus expected wins. The most direct measure of luck.
    - **Schedule Luck Index**: Difference between opponent's actual score and their season average. Positive = you faced tough opponents (unlucky).
    - **Close Games**: Games decided by <10 points. Essentially coin flips.
    - **Composite Luck Score**: 0-100 scale combining all factors (50 = average luck).
    """
    )

    advanced_df = load_advanced_luck()

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
                "composite_luck_score",
                "luck_rating",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "actual_record": "Actual Record",
            "expected_wins": st.column_config.NumberColumn(
                "Expected Wins", help="Based on all-play win percentage", format="%.2f"
            ),
            "wins_over_expected": st.column_config.NumberColumn(
                "Wins Over Expected",
                help="Actual - Expected (best luck metric)",
                format="%.2f",
            ),
            "composite_luck_score": st.column_config.ProgressColumn(
                "Luck Score",
                help="0-100 scale, 50 = average",
                format="%.1f",
                min_value=0,
                max_value=100,
            ),
            "luck_rating": "Luck Rating",
        },
    )

    # Expandable sections for nerds who want MORE detail
    with st.expander("📊 All-Play Record Details"):
        st.markdown(
            "**What is All-Play Record?** If you played every team in the league each week, this is how you'd perform."
        )
        st.dataframe(
            advanced_df[
                ["manager_name", "all_play_wins", "all_play_games", "all_play_win_pct"]
            ],
            use_container_width=True,
            hide_index=True,
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
        st.dataframe(
            advanced_df[["manager_name", "schedule_luck_index", "schedule_difficulty"]],
            use_container_width=True,
            hide_index=True,
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
            "**Close Games**: Games decided by <10 points. These are basically coin flips - good indicator of luck!"
        )
        close_df = advanced_df[advanced_df["total_close_games"] > 0].copy()
        close_df["close_record"] = (
            close_df["close_wins"].astype(int).astype(str)
            + "-"
            + close_df["close_losses"].astype(int).astype(str)
        )
        st.dataframe(
            close_df[
                [
                    "manager_name",
                    "close_record",
                    "total_close_games",
                    "close_game_win_pct",
                ]
            ],
            use_container_width=True,
            hide_index=True,
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
        st.dataframe(
            advanced_df[
                ["manager_name", "avg_points", "points_stddev", "points_range"]
            ],
            use_container_width=True,
            hide_index=True,
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
        "*🤓 Methodology: Combines all-play record (60%), schedule strength (20%), and close game performance (20%) into a single composite score.*"
    )

elif page == "📈 Weekly Performance":
    st.header("Week-by-Week Performance")

    weekly_df = load_weekly_performance()

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

elif page == "🔥 Power Rankings":
    st.header("Power Rankings")
    st.markdown(
        "*Coming soon: Advanced metrics including strength of schedule, momentum, and playoff probability*"
    )

    standings_df = load_standings()

    # Simple power ranking: 50% win%, 50% points
    power_df = standings_df.copy()
    power_df["power_score"] = (
        power_df["win_pct"] * 0.5
        + (power_df["points_for"] / power_df["points_for"].max()) * 0.5
    )

    power_df = power_df.sort_values("power_score", ascending=False).reset_index(
        drop=True
    )
    power_df["rank"] = range(1, len(power_df) + 1)

    st.dataframe(
        power_df[
            [
                "rank",
                "manager_name",
                "wins",
                "losses",
                "points_for",
                "power_score",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "rank": "Rank",
            "manager_name": "Manager",
            "wins": "W",
            "losses": "L",
            "points_for": st.column_config.NumberColumn("Total PF", format="%.1f"),
            "avg_points_per_week": st.column_config.NumberColumn(
                "Avg/Week", format="%.2f"
            ),
            "luck_differential": st.column_config.NumberColumn("Luck +/-"),
            "power_score": st.column_config.ProgressColumn(
                "Power Score", format="%.3f", min_value=0, max_value=1
            ),
        },
    )

elif page == "🎯 Draft Analysis":
    st.header("🎯 Draft Performance Analysis")

    st.markdown(
        """
    **Comprehensive draft evaluation using:**
    - 📈 Value Over Replacement (VOR) **with confidence intervals**
    - 🎲 Risk-Adjusted Metrics - volatility + availability factored in
    - 🎯 Positional Scarcity Adjustments - flex positions weighted appropriately
    - 💰 Draft-Day Opportunity Cost - what you passed up at that pick
    - 📊 **NEW: Uncertainty Quantification** - grade ranges show statistical confidence
    - 📉 **NEW: Pick-Value Curve** - compare vs expected value at each pick
    """
    )

    draft_df = load_draft_performance()

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

        # NEW: Uncertainty visualization tabs
        tab1, tab2, tab3 = st.tabs(
            ["📋 Draft Board", "📊 Uncertainty Analysis", "📉 Value Curve"]
        )

        with tab1:
            # Draft picks table (ENHANCED with uncertainty)
            st.subheader("All Draft Picks")

            # Add uncertainty toggle
            show_uncertainty = st.checkbox("Show Confidence Intervals", value=True)

            display_cols = [
                "pick_no",
                "round",
                "player_name",
                "position",
                "manager_name",
                "adj_vor",
                "pick_grade",
                "value_verdict",
            ]

            if show_uncertainty:
                # Add uncertainty columns
                display_cols.insert(6, "vor_uncertainty")
                display_cols.insert(8, "grade_uncertainty")

            st.dataframe(
                filtered_df[display_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "pick_no": "Pick",
                    "round": "Rd",
                    "player_name": "Player",
                    "position": "Pos",
                    "manager_name": "Manager",
                    "adj_vor": st.column_config.NumberColumn("Adj VOR", format="%.1f"),
                    "vor_uncertainty": st.column_config.NumberColumn(
                        "VOR ±",
                        format="%.1f",
                        help="Uncertainty range (wider = more volatile)",
                    ),
                    "pick_grade": "Grade",
                    "grade_uncertainty": st.column_config.NumberColumn(
                        "Grade ±", format="%.1f", help="Grade uncertainty"
                    ),
                    "value_verdict": "Verdict",
                },
            )

            # Best/Worst picks
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏆 Best Picks")
                best = filtered_df.nlargest(5, "grade_score")
                st.dataframe(
                    best[
                        [
                            "player_name",
                            "round",
                            "pick_grade",
                            "adj_vor",
                            "grade_uncertainty",
                        ]
                    ],
                    hide_index=True,
                    column_config={
                        "player_name": "Player",
                        "round": "Round",
                        "pick_grade": "Grade",
                        "adj_vor": st.column_config.NumberColumn(
                            "Adj VOR", format="%.1f"
                        ),
                        "grade_uncertainty": st.column_config.NumberColumn(
                            "±", format="%.1f"
                        ),
                    },
                )

        with col2:
            st.subheader("💔 Worst Picks")
            worst = filtered_df.nsmallest(5, "grade_score")
            st.dataframe(
                worst[
                    [
                        "player_name",
                        "round",
                        "pick_grade",
                        "adj_vor",
                        "grade_uncertainty",
                    ]
                ],
                hide_index=True,
                column_config={
                    "player_name": "Player",
                    "round": "Round",
                    "pick_grade": "Grade",
                    "adj_vor": st.column_config.NumberColumn("Adj VOR", format="%.1f"),
                    "grade_uncertainty": st.column_config.NumberColumn(
                        "±", format="%.1f"
                    ),
                },
            )

        with tab2:
            # NEW: Uncertainty Analysis Tab
            st.subheader("📊 Confidence Interval Analysis")

            st.markdown(
                """
            **Understanding Uncertainty:**
            - **Wide confidence intervals** = High volatility, boom-or-bust player
            - **Narrow confidence intervals** = Consistent, reliable floor
            - Uncertainty decreases as season progresses (more data)
            """
            )

            # Filter to players with uncertainty data (2+ games)
            with_uncertainty = filtered_df[
                filtered_df["vor_uncertainty"].notna()
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

                # Most/Least certain players
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🎯 Most Certain (Narrow CI)")
                    certain = with_uncertainty.nsmallest(5, "vor_uncertainty")
                    st.dataframe(
                        certain[
                            [
                                "player_name",
                                "adj_vor",
                                "vor_uncertainty",
                                "consistency_tier",
                            ]
                        ],
                        hide_index=True,
                        column_config={
                            "player_name": "Player",
                            "adj_vor": st.column_config.NumberColumn(
                                "VOR", format="%.1f"
                            ),
                            "vor_uncertainty": st.column_config.NumberColumn(
                                "Uncertainty", format="%.1f"
                            ),
                            "consistency_tier": "Consistency",
                        },
                    )

                with col2:
                    st.subheader("🎲 Most Uncertain (Wide CI)")
                    uncertain = with_uncertainty.nlargest(5, "vor_uncertainty")
                    st.dataframe(
                        uncertain[
                            [
                                "player_name",
                                "adj_vor",
                                "vor_uncertainty",
                                "consistency_tier",
                            ]
                        ],
                        hide_index=True,
                        column_config={
                            "player_name": "Player",
                            "adj_vor": st.column_config.NumberColumn(
                                "VOR", format="%.1f"
                            ),
                            "vor_uncertainty": st.column_config.NumberColumn(
                                "Uncertainty", format="%.1f"
                            ),
                            "consistency_tier": "Consistency",
                        },
                    )
            else:
                st.info(
                    "📊 Uncertainty data will appear after Week 2 (need 2+ games for variance calculations)"
                )

        with tab3:
            # NEW: Pick-Value Curve Tab
            st.subheader("📉 Pick-Value Curve Analysis")

            st.markdown(
                """
            **Value vs Expected:**
            - Shows how each pick performed vs expected value at that draft position
            - **Positive = Steal** (got more value than expected)
            - **Negative = Reach** (got less value than expected)
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
                    st.dataframe(
                        steals[
                            [
                                "pick_no",
                                "player_name",
                                "expected_vor",
                                "adj_vor",
                                "value_vs_expected",
                            ]
                        ],
                        hide_index=True,
                        column_config={
                            "pick_no": "Pick",
                            "player_name": "Player",
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
                    st.subheader("📉 Biggest Reaches")
                    reaches = active_picks.nsmallest(5, "value_vs_expected")
                    st.dataframe(
                        reaches[
                            [
                                "pick_no",
                                "player_name",
                                "expected_vor",
                                "adj_vor",
                                "value_vs_expected",
                            ]
                        ],
                        hide_index=True,
                        column_config={
                            "pick_no": "Pick",
                            "player_name": "Player",
                            "expected_vor": st.column_config.NumberColumn(
                                "Expected", format="%.1f"
                            ),
                            "adj_vor": st.column_config.NumberColumn(
                                "Actual", format="%.1f"
                            ),
                            "value_vs_expected": st.column_config.NumberColumn(
                                "Deficit", format="%.1f"
                            ),
                        },
                    )
            else:
                st.info("📊 Value curve data available for active players only")

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

        # Expandable detailed metrics
        with st.expander("📊 Advanced Metrics Breakdown"):
            st.markdown(
                "**Risk Tiers**: How reliable is this player? (Elite/Stable/Moderate/Volatile)"
            )
            st.dataframe(
                filtered_df[
                    [
                        "player_name",
                        "position",
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
                    "position": "Pos",
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

        st.markdown("---")
        st.markdown(
            "*🎓 Methodology: Combines historical performance, consistency metrics, injury risk, and positional scarcity. See docs/DRAFT_ANALYSIS_METHODOLOGY.md for details.*"
        )

# Footer
st.markdown("---")
st.markdown(
    "*Data updated weekly via automated GitLab CI/CD pipeline • Built with Streamlit & DuckDB*"
)
