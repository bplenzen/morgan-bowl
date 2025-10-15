"""
Integration tests that validate ingested data against Sleeper API.

These are SOURCE OF TRUTH tests - they compare our database directly
to the Sleeper API to ensure we ingested data correctly.
"""
import os
import pytest
import httpx
import duckdb
from pathlib import Path


# Configuration
LEAGUE_ID = os.getenv("SLEEPER_LEAGUE_ID", "1260408876017143808")
DB_PATH = Path(__file__).parent.parent.parent / "data" / "warehouse.duckdb"


@pytest.fixture
def db_conn():
    """Provide database connection for tests."""
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    yield conn
    conn.close()


@pytest.fixture
def api_client():
    """Provide HTTP client for Sleeper API."""
    return httpx.Client(base_url="https://api.sleeper.app/v1", timeout=10)


class TestAPIParityWeekly:
    """Test that weekly data in DB matches Sleeper API exactly."""
    
    @pytest.mark.parametrize("week", [1, 2, 3, 4, 5, 6])
    def test_matchup_points_match_api(self, week, db_conn, api_client):
        """
        CRITICAL: Verify matchup points in DB exactly match Sleeper API.
        
        This is the most important test - if this fails, our data is wrong.
        """
        # Fetch from Sleeper API (source of truth)
        response = api_client.get(f"/league/{LEAGUE_ID}/matchups/{week}")
        response.raise_for_status()
        api_matchups = response.json()
        
        # Build dict: roster_id -> points
        api_points = {m["roster_id"]: m["points"] for m in api_matchups}
        
        # Fetch from our database
        week_padded = f"{week:02d}"
        query = f"""
            SELECT roster_id, points 
            FROM staging.matchups_week_{week_padded}
            ORDER BY roster_id
        """
        db_matchups = db_conn.execute(query).fetchall()
        db_points = {roster_id: points for roster_id, points in db_matchups}
        
        # Compare roster by roster
        assert len(db_points) == len(api_points), \
            f"Week {week}: Expected {len(api_points)} rosters, got {len(db_points)}"
        
        for roster_id, api_pts in api_points.items():
            assert roster_id in db_points, \
                f"Week {week}: Roster {roster_id} missing from database"
            
            db_pts = db_points[roster_id]
            # Allow tiny floating point differences (0.01 points)
            assert abs(api_pts - db_pts) < 0.01, \
                f"Week {week}, Roster {roster_id}: API={api_pts}, DB={db_pts}"
    
    @pytest.mark.parametrize("week", [1, 2, 3, 4, 5, 6])
    def test_matchup_ids_match_api(self, week, db_conn, api_client):
        """Verify matchup IDs in DB match API (correct pairings)."""
        response = api_client.get(f"/league/{LEAGUE_ID}/matchups/{week}")
        response.raise_for_status()
        api_matchups = response.json()
        
        # Build dict: roster_id -> matchup_id
        api_pairings = {m["roster_id"]: m["matchup_id"] for m in api_matchups}
        
        # Fetch from database
        week_padded = f"{week:02d}"
        query = f"""
            SELECT roster_id, matchup_id 
            FROM staging.matchups_week_{week_padded}
        """
        db_matchups = db_conn.execute(query).fetchall()
        db_pairings = {roster_id: matchup_id for roster_id, matchup_id in db_matchups}
        
        # Verify pairings match
        for roster_id, api_matchup_id in api_pairings.items():
            assert roster_id in db_pairings, \
                f"Week {week}: Roster {roster_id} missing"
            assert db_pairings[roster_id] == api_matchup_id, \
                f"Week {week}: Roster {roster_id} in wrong matchup. API={api_matchup_id}, DB={db_pairings[roster_id]}"


class TestLeagueDataParity:
    """Test that league and roster data matches API."""
    
    def test_league_info_matches_api(self, db_conn, api_client):
        """Verify league name and ID match API."""
        response = api_client.get(f"/league/{LEAGUE_ID}")
        response.raise_for_status()
        api_league = response.json()
        
        # Fetch from DB
        query = "SELECT league_id, name FROM staging.league"
        result = db_conn.execute(query).fetchone()
        
        assert result is not None, "League data not found in database"
        db_league_id, db_name = result
        
        assert db_league_id == api_league["league_id"], \
            f"League ID mismatch: API={api_league['league_id']}, DB={db_league_id}"
        assert db_name == api_league["name"], \
            f"League name mismatch: API={api_league['name']}, DB={db_name}"
    
    def test_all_rosters_present(self, db_conn, api_client):
        """Verify all rosters from API are in database."""
        response = api_client.get(f"/league/{LEAGUE_ID}/rosters")
        response.raise_for_status()
        api_rosters = response.json()
        
        # Get roster IDs from API
        api_roster_ids = {r["roster_id"] for r in api_rosters}
        
        # Get roster IDs from DB
        query = "SELECT roster_id FROM staging.rosters"
        db_roster_ids = {row[0] for row in db_conn.execute(query).fetchall()}
        
        assert api_roster_ids == db_roster_ids, \
            f"Roster ID mismatch. Missing: {api_roster_ids - db_roster_ids}, Extra: {db_roster_ids - api_roster_ids}"
    
    def test_all_users_present(self, db_conn, api_client):
        """Verify all users from API are in database."""
        response = api_client.get(f"/league/{LEAGUE_ID}/users")
        response.raise_for_status()
        api_users = response.json()
        
        # Get user IDs from API
        api_user_ids = {u["user_id"] for u in api_users}
        
        # Get user IDs from DB
        query = "SELECT user_id FROM staging.users"
        db_user_ids = {row[0] for row in db_conn.execute(query).fetchall()}
        
        assert api_user_ids == db_user_ids, \
            f"User ID mismatch. Missing: {api_user_ids - db_user_ids}, Extra: {db_user_ids - api_user_ids}"


class TestDataCompleteness:
    """Test that all expected data is present."""
    
    def test_all_weeks_ingested(self, db_conn):
        """Verify we have data for all expected weeks (1-6)."""
        expected_weeks = {1, 2, 3, 4, 5, 6}
        
        # Check what week tables exist
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'staging' 
            AND table_name LIKE 'matchups_week_%'
        """
        tables = db_conn.execute(query).fetchall()
        
        # Extract week numbers
        actual_weeks = set()
        for (table_name,) in tables:
            week_str = table_name.replace("matchups_week_", "")
            actual_weeks.add(int(week_str))
        
        assert actual_weeks == expected_weeks, \
            f"Missing weeks: {expected_weeks - actual_weeks}, Extra: {actual_weeks - expected_weeks}"
    
    @pytest.mark.parametrize("week", [1, 2, 3, 4, 5, 6])
    def test_week_has_all_rosters(self, week, db_conn):
        """Verify each week has exactly 12 roster entries (one per team)."""
        week_padded = f"{week:02d}"
        query = f"""
            SELECT COUNT(DISTINCT roster_id) 
            FROM staging.matchups_week_{week_padded}
        """
        count = db_conn.execute(query).fetchone()[0]
        
        assert count == 12, \
            f"Week {week}: Expected 12 rosters, found {count}"
    
    @pytest.mark.parametrize("week", [1, 2, 3, 4, 5, 6])
    def test_week_has_six_matchups(self, week, db_conn):
        """Verify each week has exactly 6 matchups (12 teams / 2)."""
        week_padded = f"{week:02d}"
        query = f"""
            SELECT COUNT(DISTINCT matchup_id) 
            FROM staging.matchups_week_{week_padded}
        """
        count = db_conn.execute(query).fetchone()[0]
        
        assert count == 6, \
            f"Week {week}: Expected 6 matchups, found {count}"


class TestDataQuality:
    """Test data quality and reasonableness."""
    
    @pytest.mark.parametrize("week", [1, 2, 3, 4, 5, 6])
    def test_points_are_reasonable(self, week, db_conn):
        """Verify all points are within reasonable bounds."""
        week_padded = f"{week:02d}"
        query = f"""
            SELECT roster_id, points 
            FROM staging.matchups_week_{week_padded}
        """
        matchups = db_conn.execute(query).fetchall()
        
        for roster_id, points in matchups:
            assert points >= 0, \
                f"Week {week}, Roster {roster_id}: Negative points ({points})"
            assert points < 300, \
                f"Week {week}, Roster {roster_id}: Suspiciously high points ({points})"
            assert points is not None, \
                f"Week {week}, Roster {roster_id}: NULL points"
    
    @pytest.mark.parametrize("week", [1, 2, 3, 4, 5, 6])
    def test_each_matchup_has_two_rosters(self, week, db_conn):
        """Verify each matchup has exactly 2 teams (head-to-head)."""
        week_padded = f"{week:02d}"
        query = f"""
            SELECT matchup_id, COUNT(*) as roster_count
            FROM staging.matchups_week_{week_padded}
            GROUP BY matchup_id
        """
        matchups = db_conn.execute(query).fetchall()
        
        for matchup_id, count in matchups:
            assert count == 2, \
                f"Week {week}, Matchup {matchup_id}: Expected 2 rosters, found {count}"
    
    def test_standings_math_is_correct(self, db_conn):
        """Verify total wins equals total losses across league."""
        query = """
            SELECT 
                SUM(wins) as total_wins,
                SUM(losses) as total_losses
            FROM main_analytics.fct_standings
        """
        result = db_conn.execute(query).fetchone()
        total_wins, total_losses = result
        
        assert total_wins == total_losses, \
            f"Wins ({total_wins}) should equal losses ({total_losses})"
    
    def test_win_percentages_calculated_correctly(self, db_conn):
        """Verify win percentages are calculated correctly."""
        query = """
            SELECT 
                roster_id,
                wins,
                losses,
                win_pct
            FROM main_analytics.fct_standings
        """
        standings = db_conn.execute(query).fetchall()
        
        for roster_id, wins, losses, win_pct in standings:
            total_games = wins + losses
            if total_games > 0:
                expected_pct = wins / total_games
                assert abs(win_pct - expected_pct) < 0.001, \
                    f"Roster {roster_id}: Win% should be {expected_pct:.3f}, got {win_pct:.3f}"
