"""Tests for ingestion pipeline functions."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
import yaml

from ingestion.models import League
from ingestion.pipeline import validate_league_configuration


@pytest.fixture
def sample_league():
    """Sample league with typical configuration."""
    return League.model_validate(
        {
            "league_id": "123456789",
            "name": "Test League",
            "season": "2024",
            "total_rosters": 12,
            "status": "in_season",
            "settings": {
                "playoff_teams": 6,
                "playoff_week_start": 15,
            },
        }
    )


@pytest.fixture
def create_dbt_config():
    """Factory fixture to create temporary dbt_project.yml files."""

    def _create_config(league_size: int, playoff_teams: int):
        """Create a temporary dbt_project.yml with given vars."""
        config_data = {
            "name": "test_dbt",
            "vars": {
                "league_size": league_size,
                "playoff_teams": playoff_teams,
            },
        }
        temp_file = NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        yaml.dump(config_data, temp_file)
        temp_file.flush()
        return Path(temp_file.name)

    return _create_config


def test_validate_league_configuration_matching(sample_league, create_dbt_config):
    """Verify validator passes when league config matches DBT vars."""
    dbt_path = create_dbt_config(league_size=12, playoff_teams=6)

    try:
        result = validate_league_configuration(sample_league, dbt_path)

        assert result["league_size_match"] is True
        assert result["playoff_teams_match"] is True
        assert result["validation_passed"] is True
    finally:
        dbt_path.unlink()


def test_validate_league_configuration_mismatched_size(
    sample_league, create_dbt_config
):
    """Verify validator detects league size mismatch."""
    dbt_path = create_dbt_config(league_size=10, playoff_teams=6)

    try:
        result = validate_league_configuration(sample_league, dbt_path)

        assert result["league_size_match"] is False
        assert result["playoff_teams_match"] is True
        assert result["validation_passed"] is False
    finally:
        dbt_path.unlink()


def test_validate_league_configuration_mismatched_playoffs(
    sample_league, create_dbt_config
):
    """Verify validator detects playoff teams mismatch."""
    dbt_path = create_dbt_config(league_size=12, playoff_teams=4)

    try:
        result = validate_league_configuration(sample_league, dbt_path)

        assert result["league_size_match"] is True
        assert result["playoff_teams_match"] is False
        assert result["validation_passed"] is False
    finally:
        dbt_path.unlink()


def test_validate_league_configuration_both_mismatched(
    sample_league, create_dbt_config
):
    """Verify validator detects multiple mismatches."""
    dbt_path = create_dbt_config(league_size=10, playoff_teams=4)

    try:
        result = validate_league_configuration(sample_league, dbt_path)

        assert result["league_size_match"] is False
        assert result["playoff_teams_match"] is False
        assert result["validation_passed"] is False
    finally:
        dbt_path.unlink()


def test_validate_league_configuration_missing_file():
    """Verify validator handles missing dbt_project.yml gracefully."""
    league = League.model_validate(
        {
            "league_id": "123",
            "name": "Test",
            "total_rosters": 12,
            "settings": {"playoff_teams": 6},
        }
    )

    # Use non-existent path
    result = validate_league_configuration(league, Path("/nonexistent/dbt_project.yml"))

    # Should return default "passing" result when file doesn't exist
    assert result["league_size_match"] is True
    assert result["playoff_teams_match"] is True
    assert result["validation_passed"] is True


def test_validate_league_configuration_missing_league_values():
    """Verify validator handles league with missing config values."""
    league = League.model_validate(
        {
            "league_id": "123",
            "name": "Test",
            # Missing total_rosters and settings
        }
    )

    # Should pass validation when league values are None (nothing to compare)
    result = validate_league_configuration(league, Path("/nonexistent/path.yml"))

    assert result["validation_passed"] is True


def test_validate_league_configuration_missing_dbt_vars(
    sample_league, create_dbt_config
):
    """Verify validator handles dbt_project.yml with missing vars section."""
    # Create config without vars
    config_data = {"name": "test_dbt"}
    temp_file = NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
    yaml.dump(config_data, temp_file)
    temp_file.flush()
    dbt_path = Path(temp_file.name)

    try:
        result = validate_league_configuration(sample_league, dbt_path)

        # Should pass when DBT vars don't exist (nothing to compare)
        assert result["validation_passed"] is True
    finally:
        dbt_path.unlink()


def test_validate_league_configuration_different_league_sizes():
    """Verify validator works with various league sizes."""
    test_cases = [
        (8, 4, True),  # Matching
        (10, 6, True),  # Matching
        (12, 6, True),  # Matching
        (14, 8, True),  # Matching
        (12, 6, False),  # Mismatched (actual=12, config=10)
    ]

    for total_rosters, playoff_teams, should_match in test_cases:
        league = League.model_validate(
            {
                "league_id": "123",
                "name": f"League {total_rosters}",
                "total_rosters": total_rosters,
                "settings": {"playoff_teams": playoff_teams},
            }
        )

        config_data = {
            "name": "test_dbt",
            "vars": {
                "league_size": 10 if not should_match else total_rosters,
                "playoff_teams": playoff_teams,
            },
        }
        temp_file = NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        yaml.dump(config_data, temp_file)
        temp_file.flush()
        dbt_path = Path(temp_file.name)

        try:
            result = validate_league_configuration(league, dbt_path)

            if should_match:
                assert result["validation_passed"] is True
            else:
                assert result["validation_passed"] is False
        finally:
            dbt_path.unlink()
