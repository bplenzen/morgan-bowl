"""Quick data exploration script for Morgan Bowl."""

import duckdb

# Connect to the database
con = duckdb.connect("data/warehouse.duckdb")

print("=" * 80)
print("MORGAN BOWL 4.0 - DATA EXPLORATION")
print("=" * 80)

# League Info
print("\n📊 LEAGUE INFO")
print("-" * 80)
league = con.execute("SELECT * FROM staging.league").fetchone()
print(f"League ID: {league[0]}")
print(f"Name: {league[1]}")

# Users
print("\n👥 USERS")
print("-" * 80)
users = con.execute(
    """
    SELECT * FROM staging.users
    ORDER BY display_name
"""
).fetchall()
print(f"Total users: {len(users)}")
for user in users:
    print(f"  - {user[1]} (ID: {user[0]})")

# Rosters
print("\n🏈 ROSTERS")
print("-" * 80)
rosters = con.execute(
    """
    SELECT
        r.roster_id,
        r.owner_id,
        u.display_name,
        array_length(r.players) as num_players
    FROM staging.rosters r
    LEFT JOIN staging.users u ON r.owner_id = u.user_id
    ORDER BY u.display_name
"""
).fetchall()
print(f"Total rosters: {len(rosters)}")
print("\n{:<10} {:<20} {:<15}".format("Roster ID", "Owner", "# Players"))
print("-" * 80)
for roster in rosters:
    roster_id, owner_id, display_name, num_players = roster
    print(f"{roster_id:<10} {display_name:<20} {num_players if num_players else 0:<15}")

# Calculate standings from matchups
print("\n📈 CURRENT STANDINGS (Based on Week 1-6 Results)")
print("-" * 80)
standings = con.execute(
    """
    WITH all_matchups AS (
        SELECT roster_id, matchup_id, points, 1 as week FROM staging.matchups_week_01
        UNION ALL SELECT roster_id, matchup_id, points, 2 FROM staging.matchups_week_02
        UNION ALL SELECT roster_id, matchup_id, points, 3 FROM staging.matchups_week_03
        UNION ALL SELECT roster_id, matchup_id, points, 4 FROM staging.matchups_week_04
        UNION ALL SELECT roster_id, matchup_id, points, 5 FROM staging.matchups_week_05
        UNION ALL SELECT roster_id, matchup_id, points, 6 FROM staging.matchups_week_06
    ),
    matchup_results AS (
        SELECT
            m1.roster_id,
            m1.week,
            m1.points as my_points,
            m2.points as opp_points,
            CASE
                WHEN m1.points > m2.points THEN 1
                WHEN m1.points < m2.points THEN 0
                ELSE 0.5
            END as win
        FROM all_matchups m1
        JOIN all_matchups m2 ON m1.matchup_id = m2.matchup_id
            AND m1.week = m2.week
            AND m1.roster_id != m2.roster_id
    )
    SELECT
        u.display_name,
        SUM(win) as wins,
        6 - SUM(win) as losses,
        ROUND(SUM(my_points), 2) as points_for,
        ROUND(AVG(my_points), 2) as avg_points
    FROM matchup_results mr
    LEFT JOIN staging.rosters r ON mr.roster_id = r.roster_id
    LEFT JOIN staging.users u ON r.owner_id = u.user_id
    GROUP BY u.display_name
    ORDER BY wins DESC, points_for DESC
"""
).fetchall()

print(f"{'Rank':<6} {'Owner':<20} {'Record':<10} {'Points For':<12} {'Avg/Week':<10}")
print("-" * 80)
for i, (display_name, wins, losses, points_for, avg_points) in enumerate(standings, 1):
    record = f"{int(wins)}-{int(losses)}"
    print(
        f"{i:<6} {display_name:<20} {record:<10} {points_for:<12.2f} {avg_points:<10.2f}"
    )

# Week 6 Matchups (most recent)
print("\n🏆 WEEK 6 MATCHUPS")
print("-" * 80)
matchups = con.execute(
    """
    SELECT
        m.matchup_id,
        m.roster_id,
        u.display_name,
        ROUND(m.points, 2) as points
    FROM staging.matchups_week_06 m
    LEFT JOIN staging.rosters r ON m.roster_id = r.roster_id
    LEFT JOIN staging.users u ON r.owner_id = u.user_id
    ORDER BY m.matchup_id, m.points DESC
"""
).fetchall()

current_matchup = None
matchup_teams = []
for matchup in matchups:
    matchup_id, roster_id, display_name, points = matchup
    if current_matchup != matchup_id:
        if matchup_teams:
            # Print previous matchup
            team1, team2 = matchup_teams
            winner = "🏆" if team1[3] > team2[3] else ""
            loser = "🏆" if team2[3] > team1[3] else ""
            print(f"  Matchup {current_matchup}:")
            print(f"    {team1[2]:<20} {team1[3]:>8.2f} {winner}")
            print(f"    {team2[2]:<20} {team2[3]:>8.2f} {loser}")
            print()
        current_matchup = matchup_id
        matchup_teams = []
    matchup_teams.append(matchup)

# Print last matchup
if matchup_teams and len(matchup_teams) == 2:
    team1, team2 = matchup_teams
    winner = "🏆" if team1[3] > team2[3] else ""
    loser = "🏆" if team2[3] > team1[3] else ""
    print(f"  Matchup {current_matchup}:")
    print(f"    {team1[2]:<20} {team1[3]:>8.2f} {winner}")
    print(f"    {team2[2]:<20} {team2[3]:>8.2f} {loser}")

# Top Scorers
print("\n🔥 TOP SCORERS (All Weeks)")
print("-" * 80)
top_scores = con.execute(
    """
    WITH all_matchups AS (
        SELECT roster_id, points, 1 as week FROM staging.matchups_week_01
        UNION ALL SELECT roster_id, points, 2 FROM staging.matchups_week_02
        UNION ALL SELECT roster_id, points, 3 FROM staging.matchups_week_03
        UNION ALL SELECT roster_id, points, 4 FROM staging.matchups_week_04
        UNION ALL SELECT roster_id, points, 5 FROM staging.matchups_week_05
        UNION ALL SELECT roster_id, points, 6 FROM staging.matchups_week_06
    )
    SELECT
        u.display_name,
        m.week,
        ROUND(m.points, 2) as points
    FROM all_matchups m
    LEFT JOIN staging.rosters r ON m.roster_id = r.roster_id
    LEFT JOIN staging.users u ON r.owner_id = u.user_id
    ORDER BY m.points DESC
    LIMIT 10
"""
).fetchall()

print(f"{'Rank':<6} {'Owner':<20} {'Week':<6} {'Points':<10}")
print("-" * 80)
for i, (display_name, week, points) in enumerate(top_scores, 1):
    print(f"{i:<6} {display_name:<20} {week:<6} {points:<10.2f}")

# Transactions Summary
print("\n💰 TRANSACTION SUMMARY")
print("-" * 80)
tx_counts = con.execute(
    """
    SELECT
        1 as week, COUNT(*) as count FROM staging.transactions_week_01
    UNION ALL SELECT 2, COUNT(*) FROM staging.transactions_week_02
    UNION ALL SELECT 3, COUNT(*) FROM staging.transactions_week_03
    UNION ALL SELECT 4, COUNT(*) FROM staging.transactions_week_04
    UNION ALL SELECT 5, COUNT(*) FROM staging.transactions_week_05
    UNION ALL SELECT 6, COUNT(*) FROM staging.transactions_week_06
    ORDER BY week
"""
).fetchall()

print(f"{'Week':<10} {'Transactions':<15}")
print("-" * 80)
total = 0
for week, count in tx_counts:
    print(f"Week {week:<5} {count:<15}")
    total += count
print("-" * 80)
print(f"{'Total':<10} {total:<15}")

print("\n" + "=" * 80)
print("💡 TIP: Use DuckDB CLI for custom queries:")
print(
    "   poetry run python -c \"import duckdb; duckdb.connect('data/warehouse.duckdb').execute('.shell')\""
)
print("=" * 80)

con.close()
