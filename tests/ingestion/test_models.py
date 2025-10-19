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


def test_league_extracts_nested_settings():
    """Verify League.model_validate() extracts settings from nested dict to top-level fields."""
    api_data = {
        "league_id": "123456789",
        "name": "Morgan Bowl",
        "season": "2024",
        "total_rosters": 12,
        "status": "in_season",
        "settings": {
            "num_teams": 12,
            "playoff_teams": 6,
            "playoff_week_start": 15,
            "waiver_budget": 200,
            "trade_deadline": 11,
        },
        "scoring_settings": {
            "rec": 1.0,
            "pass_td": 4.0,
            "rush_td": 6.0,
        },
        "roster_positions": ["QB", "RB", "WR", "TE", "FLEX", "K", "DEF"],
    }

    league = League.model_validate(api_data)

    # Verify top-level fields
    assert league.id == "123456789"
    assert league.name == "Morgan Bowl"
    assert league.season == "2024"
    assert league.total_rosters == 12
    assert league.status == "in_season"

    # Verify extracted settings
    assert league.playoff_teams == 6
    assert league.playoff_week_start == 15

    # Verify nested dicts are preserved
    assert league.settings["waiver_budget"] == 200
    assert league.settings["trade_deadline"] == 11
    assert league.scoring_settings["rec"] == 1.0
    assert league.scoring_settings["pass_td"] == 4.0


def test_league_handles_missing_settings_fields():
    """Verify League model handles missing nested settings gracefully."""
    api_data = {
        "league_id": "123456789",
        "name": "Test League",
        "season": "2024",
        "total_rosters": 10,
        "status": "pre_draft",
        # Settings dict exists but missing some fields
        "settings": {
            "num_teams": 10,
            # Missing playoff_teams and playoff_week_start
        },
    }

    league = League.model_validate(api_data)

    assert league.id == "123456789"
    assert league.total_rosters == 10
    assert league.status == "pre_draft"
    # Should be None when not provided
    assert league.playoff_teams is None
    assert league.playoff_week_start is None


def test_league_different_sizes():
    """Verify League model works with different league sizes."""
    test_cases = [
        (8, 4),  # 8-team league, 4 playoff spots
        (10, 4),  # 10-team league, 4 playoff spots
        (12, 6),  # 12-team league, 6 playoff spots
        (14, 6),  # 14-team league, 6 playoff spots
    ]

    for total_rosters, playoff_teams in test_cases:
        api_data = {
            "league_id": "123456789",
            "name": f"Test League {total_rosters}",
            "total_rosters": total_rosters,
            "settings": {
                "playoff_teams": playoff_teams,
                "playoff_week_start": 15,
            },
        }

        league = League.model_validate(api_data)

        assert league.total_rosters == total_rosters
        assert league.playoff_teams == playoff_teams


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
