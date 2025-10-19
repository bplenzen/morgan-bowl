from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class IngestionConfig:
    """Configuration for data ingestion.

    Args:
        league_id: Sleeper league identifier
        season: Fantasy football season year
        database_path: Path to DuckDB database file
    """

    league_id: str
    season: int
    database_path: Path


def load_config() -> IngestionConfig:
    """Load ingestion configuration from environment variables.

    Required env vars:
        SLEEPER_LEAGUE_ID: League identifier
        SLEEPER_SEASON: Season year
        DUCKDB_PATH: Path to database (defaults to data/warehouse.duckdb)

    Raises:
        ConfigurationError: If required config is missing or invalid
    """
    league_id = os.getenv("SLEEPER_LEAGUE_ID")
    if not league_id:
        raise ConfigurationError("Missing required env var SLEEPER_LEAGUE_ID")

    season_raw = os.getenv("SLEEPER_SEASON")
    if not season_raw:
        raise ConfigurationError("Missing required env var SLEEPER_SEASON")

    try:
        season = int(season_raw)
    except ValueError as exc:
        raise ConfigurationError("SLEEPER_SEASON must be an integer") from exc

    # Default to data/warehouse.duckdb if not specified
    database_path = Path(os.getenv("DUCKDB_PATH", "data/warehouse.duckdb"))

    # Ensure parent directory exists
    if database_path.parent != Path("."):
        database_path.parent.mkdir(parents=True, exist_ok=True)

    return IngestionConfig(
        league_id=league_id,
        season=season,
        database_path=database_path,
    )
