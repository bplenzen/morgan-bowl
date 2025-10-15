from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping, Sequence

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ingestion.client import SleeperClient
from ingestion.config import IngestionConfig
from ingestion.models import League, Matchup, Roster, Transaction, User
from ingestion.persistence import DataStore

logger = structlog.get_logger("morgan_bowl.ingestion")


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
    run_id = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    logger.info(
        "ingestion_started",
        run_id=run_id,
        league_id=config.league_id,
        weeks=list(weeks),
    )

    try:
        # Validate all weeks before starting
        for week in weeks:
            validate_week_range(week, config.season)

        # Fetch and store league data
        league: League = _fetch_with_retry(client, "get_league", config.league_id)
        users: list[User] = _fetch_with_retry(client, "get_users", config.league_id)
        rosters: list[Roster] = _fetch_with_retry(client, "get_rosters", config.league_id)

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