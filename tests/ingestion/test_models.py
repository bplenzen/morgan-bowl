"""Tests for ingestion data models."""

from ingestion.models import League, Matchup, Roster


def test_league_parses_season():
    """Verify League model correctly parses season field from API response."""
    api_data = {
        "league_id": "123456789",
        "name": "Morgan Bowl",
        "season": "2024",  # API returns as string
    }

    league = League(**api_data)

    assert league.id == "123456789"
    assert league.name == "Morgan Bowl"
    assert league.season == "2024"


def test_league_handles_missing_season():
    """Verify League model handles missing season gracefully."""
    api_data = {
        "league_id": "123456789",
        "name": "Test League",
        # No season field
    }

    league = League(**api_data)

    assert league.id == "123456789"
    assert league.season is None


def test_matchup_parses_correctly():
    """Verify Matchup model parses key fields."""
    api_data = {"matchup_id": 1, "roster_id": 5, "points": 125.5}

    matchup = Matchup(**api_data)

    assert matchup.matchup_id == 1
    assert matchup.roster_id == 5
    assert matchup.points == 125.5


def test_roster_parses_correctly():
    """Verify Roster model parses key fields."""
    api_data = {"roster_id": 3, "owner_id": "987654321"}

    roster = Roster(**api_data)

    assert roster.roster_id == 3
    assert roster.owner_id == "987654321"
