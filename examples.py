"""
Morgan Bowl Analytics - Simple Examples

This shows you what you can actually DO with your DBT pipeline.
"""

import duckdb

# Connect to your database
con = duckdb.connect("data/warehouse.duckdb")

print("=" * 80)
print("MORGAN BOWL ANALYTICS - WHAT YOU CAN DO")
print("=" * 80)

# ============================================================================
# EXAMPLE 1: Get Current Standings
# ============================================================================
print("\n📊 EXAMPLE 1: Current League Standings")
print("-" * 80)
print("\nBefore DBT: You had to write complex SQL to calculate standings")
print("After DBT: Just query the pre-built table!\n")

standings = con.execute(
    """
    SELECT
        manager_name,
        wins,
        losses,
        ROUND(points_for, 2) as total_points,
        ROUND(points_against, 2) as points_against,
        ROUND(win_pct * 100, 1) as win_pct
    FROM main_analytics.fct_standings
    ORDER BY wins DESC, total_points DESC
    LIMIT 5
"""
).fetchall()

print(f"{'Manager':<20} {'W-L':<10} {'PF':<10} {'PA':<10} {'Win%':<10}")
print("-" * 80)
for name, w, losses, pf, pa, pct in standings:
    print(f"{name:<20} {w}-{losses:<8} {pf:<10.1f} {pa:<10.1f} {pct}%")

# ============================================================================
# EXAMPLE 2: Head-to-Head Records
# ============================================================================
print("\n\n🏆 EXAMPLE 2: Head-to-Head Matchup History")
print("-" * 80)
print("See how you've done against specific opponents\n")

# Let's see your (bplenzen) record vs jamespancakes (the leader)
h2h = con.execute(
    """
    SELECT
        week,
        manager_name,
        ROUND(points, 2) as your_points,
        opponent_manager_name,
        ROUND(opponent_points, 2) as their_points,
        CASE
            WHEN win_flag = 1 THEN 'WIN'
            WHEN win_flag = 0 THEN 'LOSS'
        END as result
    FROM main_analytics.fct_matchups
    WHERE manager_name = 'bplenzen'
        AND opponent_manager_name = 'jamespancakes'
    ORDER BY week
"""
).fetchall()

if h2h:
    print("YOU (bplenzen) vs jamespancakes:")
    for week, you, your_pts, them, their_pts, result in h2h:
        print(
            f"  Week {week}: You scored {your_pts}, they scored {their_pts} - {result}"
        )
else:
    print("Haven't played jamespancakes yet!")

# ============================================================================
# EXAMPLE 3: Weekly Performance Trends
# ============================================================================
print("\n\n📈 EXAMPLE 3: Your Weekly Scoring Trend")
print("-" * 80)
print("Track your points week-by-week\n")

weekly = con.execute(
    """
    SELECT
        week,
        ROUND(points, 2) as points,
        ROUND(opponent_points, 2) as opp_points,
        CASE WHEN win_flag = 1 THEN 'W' ELSE 'L' END as result
    FROM main_analytics.fct_matchups
    WHERE manager_name = 'bplenzen'
    ORDER BY week
"""
).fetchall()

print(f"{'Week':<8} {'Your Pts':<12} {'Opp Pts':<12} {'Result':<8}")
print("-" * 80)
total = 0
for week, pts, opp, result in weekly:
    total += pts
    print(f"Week {week:<3} {pts:<12.1f} {opp:<12.1f} {result:<8}")
avg = total / len(weekly) if weekly else 0
print("-" * 80)
print(f"Average: {avg:.1f} points per week")

# ============================================================================
# EXAMPLE 4: Luck Index (Points vs Record)
# ============================================================================
print("\n\n🍀 EXAMPLE 4: The 'Luck Index' - Who's Overperforming/Underperforming?")
print("-" * 80)
print("High points but low wins = UNLUCKY (bad scheduling)")
print("Low points but high wins = LUCKY (easy schedule)\n")

luck = con.execute(
    """
    SELECT
        manager_name,
        wins,
        ROUND(points_for, 2) as points,
        ROUND(points_for / 6, 2) as avg_points,
        -- Calculate expected wins based on points
        ROUND(6.0 * (points_for - 600) / 300, 1) as expected_wins,
        ROUND(wins - (6.0 * (points_for - 600) / 300), 1) as luck_factor
    FROM main_analytics.fct_standings
    ORDER BY luck_factor DESC
"""
).fetchall()

print(f"{'Manager':<20} {'Wins':<8} {'Avg Pts':<12} {'Expected':<12} {'Luck':<10}")
print("-" * 80)
for name, wins, pts, avg, exp_w, luck in luck:
    luck_emoji = "🍀" if luck > 0.5 else "😢" if luck < -0.5 else "😐"
    print(f"{name:<20} {wins:<8} {avg:<12.1f} {exp_w:<12.1f} {luck:>+.1f} {luck_emoji}")

# ============================================================================
# EXAMPLE 5: Best/Worst Performances
# ============================================================================
print("\n\n💥 EXAMPLE 5: Biggest Blowouts & Closest Games")
print("-" * 80)

blowouts = con.execute(
    """
    SELECT
        week,
        manager_name,
        ROUND(points, 2) as winner_pts,
        opponent_manager_name,
        ROUND(opponent_points, 2) as loser_pts,
        ROUND(point_diff, 2) as margin
    FROM main_analytics.fct_matchups
    WHERE win_flag = 1
    ORDER BY ABS(point_diff) DESC
    LIMIT 3
"""
).fetchall()

print("\nBiggest Blowouts:")
for week, winner, w_pts, loser, l_pts, margin in blowouts:
    print(
        f"  Week {week}: {winner} ({w_pts}) destroyed {loser} ({l_pts}) by {margin} pts"
    )

nail_biters = con.execute(
    """
    SELECT
        week,
        manager_name,
        ROUND(points, 2) as winner_pts,
        opponent_manager_name,
        ROUND(opponent_points, 2) as loser_pts,
        ROUND(point_diff, 2) as margin
    FROM main_analytics.fct_matchups
    WHERE win_flag = 1
    ORDER BY ABS(point_diff) ASC
    LIMIT 3
"""
).fetchall()

print("\nClosest Games (Nail-biters):")
for week, winner, w_pts, loser, l_pts, margin in nail_biters:
    print(
        f"  Week {week}: {winner} ({w_pts}) barely beat {loser} ({l_pts}) by {margin} pts"
    )

# ============================================================================
print("\n" + "=" * 80)
print("💡 THE POINT: DBT did all the hard work for you!")
print("=" * 80)
print(
    """
Instead of writing complex SQL every time:
  ❌ Manually joining matchups, rosters, users
  ❌ Calculating wins/losses from point differentials
  ❌ Aggregating across multiple week tables

You now just query clean tables:
  ✅ fct_matchups - every game with all the details
  ✅ fct_standings - pre-calculated standings

Want to build a dashboard? A Slack bot? A weekly report?
Just query these tables - the hard work is already done!
"""
)

print("\n📚 Try it yourself:")
print("  poetry run python examples.py")
print("  (or modify this file to create your own queries!)")
print("=" * 80)

con.close()
