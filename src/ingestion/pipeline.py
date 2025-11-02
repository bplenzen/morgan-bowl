from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import structlog
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential

from ingestion.client import SleeperClient
from ingestion.config import IngestionConfig
from ingestion.models import League, Matchup, Roster, Transaction, User
from ingestion.persistence import DataStore

logger = structlog.get_logger("morgan_bowl.ingestion")


def validate_league_configuration(
    league: League, dbt_project_path: Path | None = None
) -> dict[str, bool]:
    """Validate that league configuration matches DBT project variables.

    Args:
        league: League object from Sleeper API with detected configuration
        dbt_project_path: Optional path to dbt_project.yml (defaults to dbt/dbt_project.yml)

    Returns:
        Dict with validation results: {
            "league_size_match": bool,
            "playoff_teams_match": bool,
            "validation_passed": bool
        }
    """
    validation_results = {
        "league_size_match": True,
        "playoff_teams_match": True,
        "validation_passed": True,
    }

    # Default to dbt/dbt_project.yml if not provided
    if dbt_project_path is None:
        dbt_project_path = (
            Path(__file__).parent.parent.parent / "dbt" / "dbt_project.yml"
        )

    # If dbt_project.yml doesn't exist, skip validation
    if not dbt_project_path.exists():
        logger.warning(
            "dbt_project.yml not found, skipping configuration validation",
            path=str(dbt_project_path),
        )
        return validation_results

    try:
        # Load DBT project variables
        with open(dbt_project_path, "r") as f:
            dbt_config = yaml.safe_load(f)

        dbt_vars = dbt_config.get("vars", {})
        dbt_league_size = dbt_vars.get("league_size")
        dbt_playoff_teams = dbt_vars.get("playoff_teams")

        # Validate league size
        if league.total_rosters and dbt_league_size:
            if league.total_rosters != dbt_league_size:
                validation_results["league_size_match"] = False
                validation_results["validation_passed"] = False
                logger.warning(
                    "League size mismatch detected",
                    detected=league.total_rosters,
                    dbt_config=dbt_league_size,
                    recommendation="DBT models now use auto-detected values. Consider removing or updating dbt_project.yml vars.",
                )

        # Validate playoff teams
        if league.playoff_teams and dbt_playoff_teams:
            if league.playoff_teams != dbt_playoff_teams:
                validation_results["playoff_teams_match"] = False
                validation_results["validation_passed"] = False
                logger.warning(
                    "Playoff teams mismatch detected",
                    detected=league.playoff_teams,
                    dbt_config=dbt_playoff_teams,
                    recommendation="DBT models now use auto-detected values. Consider removing or updating dbt_project.yml vars.",
                )

        # Log success if everything matches
        if validation_results["validation_passed"]:
            logger.info(
                "League configuration validated successfully",
                total_rosters=league.total_rosters,
                playoff_teams=league.playoff_teams,
                playoff_week_start=league.playoff_week_start,
            )

    except Exception as e:
        logger.error(
            "Failed to validate league configuration",
            error=str(e),
            path=str(dbt_project_path),
        )
        # Don't fail ingestion on validation errors

    return validation_results


def _dump(model) -> Mapping:
    return model.model_dump(by_alias=True)


def _dump_many(models: Iterable) -> list[Mapping]:
    return [_dump(model) for model in models]


def validate_week_range(week: int, season: int = 2025) -> bool:
    """Validate that a week number is valid for the given season."""
    if week < 1 or week > 18:
        raise ValueError(f"Week {week} is invalid. Must be between 1 and 18.")

    # Check if week is in the future
    current_date = datetime.now()
    if season > current_date.year or (season == current_date.year and week > 18):
        logger.warning("Attempting to fetch future week data", week=week, season=season)
    return True


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
)
def _fetch_with_retry(client: SleeperClient, method_name: str, *args, **kwargs):
    """Fetch data from Sleeper API with retries."""
    method = getattr(client, method_name)
    try:
        return method(*args, **kwargs)
    except Exception as e:
        logger.error(
            "Error fetching from Sleeper API",
            method=method_name,
            error=str(e),
            args=args,
            kwargs=kwargs,
        )
        raise


def run_ingestion(
    *,
    config: IngestionConfig,
    client: SleeperClient,
    store: DataStore,
    weeks: Sequence[int],
) -> dict:
    """Run the ingestion pipeline with retries and validation.

    Args:
        config: Ingestion configuration
        client: Sleeper API client
        store: Data store for persistence
        weeks: Sequence of week numbers to ingest

    Returns:
        Dict containing run summary

    Raises:
        ValueError: If week validation fails
        Exception: If API calls or data processing fails
    """
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    logger.info(
        "ingestion_started",
        run_id=run_id,
        league_id=config.league_id,
        weeks=list(weeks),
    )

    try:
        # Fetch league data first to get the season
        league: League = _fetch_with_retry(client, "get_league", config.league_id)

        # Auto-detect season from league data (fallback to config if not available)
        season = int(league.season) if league.season else config.season
        logger.info(
            "Using season from league data", season=season, league_name=league.name
        )

        # Validate league configuration against DBT project vars
        validation_results = validate_league_configuration(league)

        # Validate all weeks before starting
        for week in weeks:
            validate_week_range(week, season)

        # Fetch other league data
        users: list[User] = _fetch_with_retry(client, "get_users", config.league_id)
        rosters: list[Roster] = _fetch_with_retry(
            client, "get_rosters", config.league_id
        )

        store.write_table("league", [_dump(league)])
        store.write_table("users", _dump_many(users))
        store.write_table("rosters", _dump_many(rosters))

        matchup_counts: dict[str, int] = {}
        transaction_counts: dict[str, int] = {}

        # Fetch and store weekly data
        for week in weeks:
            try:
                matchups: list[Matchup] = _fetch_with_retry(
                    client, "get_matchups", config.league_id, week=week
                )
                transactions: list[Transaction] = _fetch_with_retry(
                    client, "get_transactions", config.league_id, week=week
                )

                matchup_label = f"matchups_week_{week:02d}"
                transaction_label = f"transactions_week_{week:02d}"

                store.write_table(matchup_label, _dump_many(matchups))
                store.write_table(transaction_label, _dump_many(transactions))

                matchup_counts[f"week_{week:02d}"] = len(matchups)
                transaction_counts[f"week_{week:02d}"] = len(transactions)

            except Exception as e:
                logger.error(
                    "Failed to process week data",
                    week=week,
                    error=str(e),
                    league_id=config.league_id,
                )
                raise

        # Create run summary
        summary = {
            "run_id": run_id,
            "league": _dump(league),
            "validation": validation_results,
            "counts": {
                "users": len(users),
                "rosters": len(rosters),
                "matchups": matchup_counts,
                "transactions": transaction_counts,
            },
        }

        logger.info(
            "ingestion_completed",
            run_id=run_id,
            counts=summary["counts"],
        )
        return summary

    except Exception as e:
        logger.error(
            "Ingestion failed",
            error=str(e),
            run_id=run_id,
            league_id=config.league_id,
        )
        raise
