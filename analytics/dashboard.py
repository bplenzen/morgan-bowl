"""
🏈 Morgan Bowl Fantasy Football Dashboard
Interactive analytics for league members to explore standings, luck, and performance.
"""

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Morgan Bowl Analytics",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
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
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_db_connection():
    """Connect to DuckDB warehouse"""
    db_path = Path(__file__).parent.parent / "data" / "warehouse.duckdb"
    return duckdb.connect(str(db_path), read_only=True)

@st.cache_data
def load_standings():
    """Load current standings"""
    conn = get_db_connection()
    return conn.execute("""
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
    """).df()

@st.cache_data
def load_justice_record():
    """Load justice record (luck analysis)"""
    conn = get_db_connection()
    return conn.execute("""
        SELECT 
            manager_name,
            actual_wins,
            actual_losses,
            justice_wins,
            justice_losses,
            luck_differential,
            luck_status,
            round(avg_points_per_week, 2) as avg_points_per_week
        FROM main_analytics.fct_justice_record
        ORDER BY luck_differential DESC
    """).df()

@st.cache_data
def load_weekly_performance():
    """Load week-by-week performance"""
    conn = get_db_connection()
    return conn.execute("""
        SELECT 
            week,
            manager_name,
            round(points, 2) as points,
            round(opponent_points, 2) as opponent_points,
            opponent_manager_name,
            win_flag
        FROM main_analytics.fct_matchups
        ORDER BY week, points DESC
    """).df()

@st.cache_data
def load_advanced_luck():
    """Load advanced luck metrics (the nerd shit)"""
    conn = get_db_connection()
    return conn.execute("""
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
    """).df()

# Header
st.title("🏈 Morgan Bowl Fantasy Football Analytics")
st.markdown("*Data-driven insights for the most competitive fantasy league*")

# Sidebar
with st.sidebar:
    st.image("https://sleepercdn.com/images/v2/icons/football/nfl_default.png", width=100)
    st.markdown("## Navigation")
    page = st.radio(
        "Choose a view:",
        ["📊 Standings", "🍀 Justice Rankings", "🤓 Nerd Shit", "📈 Weekly Performance", "🔥 Power Rankings"]
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This dashboard analyzes your fantasy football league using:
    - **Actual Record**: Head-to-head wins/losses
    - **Justice Rankings**: Simple top-6/bottom-6 approach
    - **Nerd Shit**: Advanced statistical luck analysis
    """)

# Main content
if page == "📊 Standings":
    st.header("Current Standings")
    
    standings_df = load_standings()
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        leader = standings_df.iloc[0]
        st.metric("League Leader", leader['manager_name'], f"{leader['wins']}-{leader['losses']}")
    with col2:
        highest_scorer = standings_df.nlargest(1, 'points_for').iloc[0]
        st.metric("Highest Scorer", highest_scorer['manager_name'], f"{highest_scorer['points_for']:.1f} pts")
    with col3:
        avg_points = standings_df['points_for'].mean()
        st.metric("Avg Points For", f"{avg_points:.1f}")
    with col4:
        total_weeks = standings_df['wins'].iloc[0] + standings_df['losses'].iloc[0]
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
        }
    )
    
    # Points visualization
    fig = px.bar(
        standings_df.sort_values('points_for', ascending=True),
        x='points_for',
        y='manager_name',
        orientation='h',
        title='Total Points Scored',
        labels={'points_for': 'Points', 'manager_name': 'Manager'},
        color='win_pct',
        color_continuous_scale='RdYlGn'
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "🍀 Justice Rankings":
    st.header("Justice Rankings - Who's Lucky? Who's Unlucky?")
    
    st.markdown("""
    **How it works:** Each week, the top 6 scorers get a "justice win" and the bottom 6 get a "justice loss". 
    Your **justice record** is what your record *should* be based on scoring. Compare it to your actual record to see luck!
    
    *This is the simple approach. For advanced stats nerds, check out "🤓 Nerd Shit".*
    """)
    
    justice_df = load_justice_record()
    
    # Luck metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        luckiest = justice_df.nlargest(1, 'luck_differential').iloc[0]
        st.metric("Luckiest Team", luckiest['manager_name'], f"+{luckiest['luck_differential']}")
    with col2:
        unluckiest = justice_df.nsmallest(1, 'luck_differential').iloc[0]
        st.metric("Unluckiest Team", unluckiest['manager_name'], f"{unluckiest['luck_differential']}")
    with col3:
        fair_teams = len(justice_df[justice_df['luck_differential'] == 0])
        st.metric("Fair Teams", fair_teams, "⚖️")
    
    # Justice record table
    st.subheader("Justice Record Breakdown")
    justice_df['actual_record'] = justice_df['actual_wins'].astype(int).astype(str) + '-' + justice_df['actual_losses'].astype(int).astype(str)
    justice_df['justice_record'] = justice_df['justice_wins'].astype(int).astype(str) + '-' + justice_df['justice_losses'].astype(int).astype(str)
    
    st.dataframe(
        justice_df[['manager_name', 'actual_record', 'justice_record', 'luck_differential', 'luck_status', 'avg_points_per_week']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "actual_record": "Actual Record",
            "justice_record": "Justice Record",
            "luck_differential": st.column_config.NumberColumn("Luck +/-", help="Positive = lucky, Negative = unlucky"),
            "luck_status": "Status",
            "avg_points_per_week": st.column_config.NumberColumn("Avg Pts/Week", format="%.2f"),
        }
    )
    
    # Luck visualization
    fig = go.Figure()
    
    colors = ['red' if x < 0 else 'green' if x > 0 else 'gray' for x in justice_df['luck_differential']]
    
    fig.add_trace(go.Bar(
        x=justice_df['manager_name'],
        y=justice_df['luck_differential'],
        marker_color=colors,
        text=justice_df['luck_differential'],
        textposition='outside',
        name='Luck Differential'
    ))
    
    fig.update_layout(
        title='Luck Differential (Actual Wins - Justice Wins)',
        xaxis_title='Manager',
        yaxis_title='Luck +/-',
        yaxis_zeroline=True,
        yaxis_zerolinewidth=2,
        yaxis_zerolinecolor='black',
        showlegend=False,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

elif page == "🤓 Nerd Shit":
    st.header("🤓 Advanced Luck Analytics (Nerd Shit)")
    
    st.markdown("""
    **For the data nerds**: This uses advanced statistical methods to calculate luck more precisely than the simple Justice Rankings.
    
    **Key Metrics:**
    - **Expected Wins**: Based on "all-play" record (if you played everyone each week, what % would you win?)
    - **Wins Over Expected**: Your actual wins minus expected wins (most accurate luck metric)
    - **Schedule Luck**: Did you face opponents on their hot weeks or cold weeks?
    - **Close Game Record**: Performance in games decided by <10 points
    - **Composite Luck Score**: 0-100 scale combining all factors (50 = average)
    """)
    
    advanced_df = load_advanced_luck()
    
    # Top metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        luckiest = advanced_df.iloc[0]
        st.metric("Luckiest (Statistically)", luckiest['manager_name'], f"{luckiest['composite_luck_score']}/100")
    with col2:
        unluckiest = advanced_df.iloc[-1]
        st.metric("Unluckiest (Statistically)", unluckiest['manager_name'], f"{unluckiest['composite_luck_score']}/100")
    with col3:
        avg_luck = advanced_df['composite_luck_score'].mean()
        st.metric("League Avg Luck", f"{avg_luck:.1f}/100", "⚖️")
    
    # Main table
    st.subheader("Advanced Luck Breakdown")
    
    # Create display record
    advanced_df['actual_record'] = advanced_df['actual_wins'].astype(int).astype(str) + '-' + advanced_df['actual_losses'].astype(int).astype(str)
    
    st.dataframe(
        advanced_df[['manager_name', 'actual_record', 'expected_wins', 'wins_over_expected', 'composite_luck_score', 'luck_rating']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "actual_record": "Actual Record",
            "expected_wins": st.column_config.NumberColumn("Expected Wins", help="Based on all-play win percentage", format="%.2f"),
            "wins_over_expected": st.column_config.NumberColumn("Wins Over Expected", help="Actual - Expected (best luck metric)", format="%.2f"),
            "composite_luck_score": st.column_config.ProgressColumn("Luck Score", help="0-100 scale, 50 = average", format="%.1f", min_value=0, max_value=100),
            "luck_rating": "Luck Rating",
        }
    )
    
    # Expandable sections for nerds who want MORE detail
    with st.expander("📊 All-Play Record Details"):
        st.markdown("**What is All-Play Record?** If you played every team in the league each week, this is how you'd perform.")
        st.dataframe(
            advanced_df[['manager_name', 'all_play_wins', 'all_play_games', 'all_play_win_pct']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "manager_name": "Manager",
                "all_play_wins": st.column_config.NumberColumn("All-Play Wins", help="Total wins if you played everyone"),
                "all_play_games": st.column_config.NumberColumn("All-Play Games", help="Total possible matchups"),
                "all_play_win_pct": st.column_config.NumberColumn("All-Play Win %", format="%.3f"),
            }
        )
    
    with st.expander("📅 Schedule Luck Analysis"):
        st.markdown("**Schedule Luck**: Positive numbers = you faced opponents on their good weeks (unlucky), negative = faced them on bad weeks (lucky)")
        st.dataframe(
            advanced_df[['manager_name', 'schedule_luck_index', 'schedule_difficulty']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "manager_name": "Manager",
                "schedule_luck_index": st.column_config.NumberColumn("Schedule Index", help="Higher = tougher opponents", format="%.2f"),
                "schedule_difficulty": "Difficulty Rating",
            }
        )
    
    with st.expander("🎲 Close Game Performance"):
        st.markdown("**Close Games**: Games decided by <10 points. These are basically coin flips - good indicator of luck!")
        close_df = advanced_df[advanced_df['total_close_games'] > 0].copy()
        close_df['close_record'] = close_df['close_wins'].astype(int).astype(str) + '-' + close_df['close_losses'].astype(int).astype(str)
        st.dataframe(
            close_df[['manager_name', 'close_record', 'total_close_games', 'close_game_win_pct']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "manager_name": "Manager",
                "close_record": "Close Game Record",
                "total_close_games": "Total Close Games",
                "close_game_win_pct": st.column_config.NumberColumn("Close Game Win %", format="%.3f"),
            }
        )
    
    with st.expander("📉 Consistency Metrics"):
        st.markdown("**Consistency**: How much do your scores vary week-to-week?")
        st.dataframe(
            advanced_df[['manager_name', 'avg_points', 'points_stddev', 'points_range']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "manager_name": "Manager",
                "avg_points": st.column_config.NumberColumn("Avg Points", format="%.2f"),
                "points_stddev": st.column_config.NumberColumn("Std Deviation", help="Lower = more consistent", format="%.2f"),
                "points_range": st.column_config.NumberColumn("Range (Max-Min)", help="Difference between best and worst week", format="%.2f"),
            }
        )
    
    # Visualization: Composite Luck Score
    st.subheader("Composite Luck Score Distribution")
    
    fig = go.Figure()
    
    # Color by luck level
    colors = []
    for score in advanced_df['composite_luck_score']:
        if score >= 65:
            colors.append('#2ecc71')  # Very lucky - green
        elif score >= 55:
            colors.append('#a8e6cf')  # Lucky - light green
        elif score >= 45:
            colors.append('#95a5a6')  # Fair - gray
        elif score >= 35:
            colors.append('#f39c12')  # Unlucky - orange
        else:
            colors.append('#e74c3c')  # Very unlucky - red
    
    fig.add_trace(go.Bar(
        x=advanced_df['manager_name'],
        y=advanced_df['composite_luck_score'],
        marker_color=colors,
        text=advanced_df['composite_luck_score'],
        textposition='outside',
        name='Luck Score'
    ))
    
    # Add reference line at 50 (average)
    fig.add_hline(y=50, line_dash="dash", line_color="black", annotation_text="Average (50)")
    
    fig.update_layout(
        title='Composite Luck Score (0-100 scale)',
        xaxis_title='Manager',
        yaxis_title='Luck Score',
        yaxis_range=[0, 100],
        showlegend=False,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("*🤓 Methodology: Combines all-play record (60%), schedule strength (20%), and close game performance (20%) into a single composite score.*")

elif page == "📈 Weekly Performance":
    st.header("Week-by-Week Performance")
    
    weekly_df = load_weekly_performance()
    
    # Week selector
    weeks = sorted(weekly_df['week'].unique())
    selected_week = st.selectbox("Select Week", weeks, index=len(weeks)-1)
    
    week_data = weekly_df[weekly_df['week'] == selected_week].copy()
    week_data['result'] = week_data['win_flag'].map({1: '✅ Win', 0: '❌ Loss'})
    
    # Week summary
    col1, col2, col3 = st.columns(3)
    with col1:
        highest = week_data.nlargest(1, 'points').iloc[0]
        st.metric("Highest Score", highest['manager_name'], f"{highest['points']:.2f} pts")
    with col2:
        lowest = week_data.nsmallest(1, 'points').iloc[0]
        st.metric("Lowest Score", lowest['manager_name'], f"{lowest['points']:.2f} pts")
    with col3:
        avg_score = week_data['points'].mean()
        st.metric("Average Score", f"{avg_score:.2f} pts")
    
    # Matchup results
    st.subheader(f"Week {selected_week} Matchups")
    st.dataframe(
        week_data[['manager_name', 'points', 'opponent_manager_name', 'opponent_points', 'result']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "manager_name": "Manager",
            "points": st.column_config.NumberColumn("Score", format="%.2f"),
            "opponent_manager_name": "Opponent",
            "opponent_points": st.column_config.NumberColumn("Opp Score", format="%.2f"),
            "result": "Result",
        }
    )
    
    # Weekly scoring trends
    st.subheader("Scoring Trends Across All Weeks")
    manager = st.selectbox("Select Manager", sorted(weekly_df['manager_name'].unique()))
    
    manager_data = weekly_df[weekly_df['manager_name'] == manager].sort_values('week')
    
    # Calculate league average per week
    league_avg = weekly_df.groupby('week')['points'].mean().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=manager_data['week'],
        y=manager_data['points'],
        mode='lines+markers',
        name='Points Scored',
        line=dict(color='blue', width=3),
        marker=dict(size=10)
    ))
    fig.add_trace(go.Scatter(
        x=manager_data['week'],
        y=manager_data['opponent_points'],
        mode='lines+markers',
        name='Opponent Points',
        line=dict(color='red', width=2, dash='dash'),
        marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=league_avg['week'],
        y=league_avg['points'],
        mode='lines',
        name='League Average',
        line=dict(color='green', width=2, dash='dot'),
        opacity=0.7
    ))
    
    fig.update_layout(
        title=f'{manager} - Weekly Scoring',
        xaxis_title='Week',
        yaxis_title='Points',
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

elif page == "🔥 Power Rankings":
    st.header("Power Rankings")
    st.markdown("*Coming soon: Advanced metrics including strength of schedule, momentum, and playoff probability*")
    
    standings_df = load_standings()
    justice_df = load_justice_record()
    
    # Combine for power ranking
    power_df = standings_df.merge(
        justice_df[['manager_name', 'luck_differential', 'avg_points_per_week']], 
        on='manager_name'
    )
    
    # Simple power ranking: 40% win%, 40% points, 20% luck-adjusted
    power_df['power_score'] = (
        power_df['win_pct'] * 0.4 +
        (power_df['points_for'] / power_df['points_for'].max()) * 0.4 +
        ((power_df['luck_differential'] + 2) / 4) * 0.2  # Normalize luck -2 to +2 -> 0 to 1
    )
    
    power_df = power_df.sort_values('power_score', ascending=False).reset_index(drop=True)
    power_df['rank'] = range(1, len(power_df) + 1)
    
    st.dataframe(
        power_df[['rank', 'manager_name', 'wins', 'losses', 'points_for', 'avg_points_per_week', 'luck_differential', 'power_score']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "rank": "Rank",
            "manager_name": "Manager",
            "wins": "W",
            "losses": "L",
            "points_for": st.column_config.NumberColumn("Total PF", format="%.1f"),
            "avg_points_per_week": st.column_config.NumberColumn("Avg/Week", format="%.2f"),
            "luck_differential": st.column_config.NumberColumn("Luck +/-"),
            "power_score": st.column_config.ProgressColumn("Power Score", format="%.3f", min_value=0, max_value=1),
        }
    )

# Footer
st.markdown("---")
st.markdown("*Data updated weekly via automated GitLab CI/CD pipeline • Built with Streamlit & DuckDB*")
