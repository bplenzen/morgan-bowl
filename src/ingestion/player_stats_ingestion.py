"""Player stats ingestion script.

Fetches weekly player statistics from Sleeper API and stores them in the database.
This should be run weekly alongside regular matchup ingestion.
"""

from __future__ import annotations

import structlog

from ingestion.client import SleeperClient
from ingestion.config import IngestionConfig, load_config
from ingestion.persistence import DataStore

logger = structlog.get_logger("morgan_bowl.player_stats_ingestion")


def ingest_player_stats(
    config: IngestionConfig,
    weeks: list[int],
    client: SleeperClient | None = None,
    store: DataStore | None = None,
) -> dict[str, int]:
    """Ingest player stats from Sleeper API for specified weeks.

    Args:
        config: Ingestion configuration
        weeks: List of week numbers to ingest (e.g., [1, 2, 3, 4, 5, 6])
        client: Optional SleeperClient (creates new one if not provided)
        store: Optional DataStore (creates new one if not provided)

    Returns:
        Dict with ingestion summary: {
            "weeks_processed": int,
            "total_player_stats": int,
        }
    """
    # Create client and store if not provided
    should_close_client = client is None

    if client is None:
        client = SleeperClient()

    if store is None:
        store = DataStore(database_path=config.database_path)

    try:
        logger.info(
            "player_stats_ingestion_started",
            season=config.season,
            weeks=weeks,
        )

        total_stats = 0

        for week in weeks:
            logger.info("fetching_player_stats", week=week)

            # Fetch stats for this week
            stats_by_player = client.get_player_stats(config.season, week)

            # Transform to list of dicts with player_id, week, and stats
            records = []
            for player_id, stats in stats_by_player.items():
                record = {
                    "player_id": player_id,
                    "week": week,
                    "season": config.season,
                    **stats,  # Unpack all stat fields
                }
                records.append(record)

            # Save to table named player_stats_week_XX
            table_name = f"player_stats_week_{week:02d}"
            store.write_table(table_name, records, mode="replace")

            logger.info(
                "player_stats_saved",
                week=week,
                table=table_name,
                players_with_stats=len(records),
            )

            total_stats += len(records)

        summary = {
            "weeks_processed": len(weeks),
            "total_player_stats": total_stats,
        }

        logger.info(
            "player_stats_ingestion_completed",
            **summary,
        )

        return summary

    finally:
        if should_close_client and client:
            client.close()


def main():
    """CLI entry point for player stats ingestion."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest player stats from Sleeper API")
    parser.add_argument(
        "--weeks",
        type=int,
        nargs="+",
        required=True,
        help="Week numbers to ingest (e.g., --weeks 1 2 3 4 5 6)",
    )

    args = parser.parse_args()
    config = load_config()

    logger.info("starting_player_stats_ingestion", weeks=args.weeks)

    summary = ingest_player_stats(config, args.weeks)

    logger.info(
        "player_stats_ingestion_summary",
        **summary,
    )

    print("\n✅ Player stats ingestion completed!")
    print(f"   - Weeks processed: {summary['weeks_processed']}")
    print(f"   - Total player-week records: {summary['total_player_stats']}")


if __name__ == "__main__":
    main()
