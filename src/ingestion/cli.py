from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import structlog

from ingestion.client import SleeperClient
from ingestion.config import ConfigurationError, IngestionConfig, load_config
from ingestion.persistence import DataStore
from ingestion.pipeline import run_ingestion

logger = structlog.get_logger("morgan_bowl.cli")

DEFAULT_WEEKS = list(range(1, 19))  # Full NFL regular season


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and store fantasy football data from Sleeper"
    )
    parser.add_argument(
        "--week",
        type=int,
        action="append",
        dest="weeks",
        help="Week to ingest (can be specified multiple times, defaults to all weeks)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        help="Override database path from config",
    )
    return parser


def resolve_weeks(weeks: list[int] | None) -> list[int]:
    """Get sorted, unique list of weeks to process."""
    if not weeks:
        return DEFAULT_WEEKS
    return sorted(set(weeks))


def main(argv: list[str] | None = None) -> int:
    """Run the ingestion pipeline.
    
    Args:
        argv: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        # Load config
        config = load_config()
        if args.db:
            config = IngestionConfig(
                league_id=config.league_id,
                season=config.season,
                database_path=args.db,
            )

        # Initialize components
        client = SleeperClient()
        store = DataStore(database_path=config.database_path)

        try:
            # Run ingestion
            summary = run_ingestion(
                config=config,
                client=client,
                store=store,
                weeks=resolve_weeks(args.weeks),
            )

            # Print summary as JSON
            print(json.dumps(summary, indent=2))
            return 0

        finally:
            client.close()

    except ConfigurationError as e:
        logger.error("configuration_error", error=str(e))
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
        
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())