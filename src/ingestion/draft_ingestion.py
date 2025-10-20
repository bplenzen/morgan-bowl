"""Draft data ingestion script.

Fetches draft picks from Sleeper API and stores them in the database.
This is typically run once at the start of the season.
"""

from __future__ import annotations

import structlog

from ingestion.client import SleeperClient
from ingestion.config import IngestionConfig, load_config
from ingestion.persistence import DataStore

logger = structlog.get_logger("morgan_bowl.draft_ingestion")


def _dump(obj) -> dict:
    """Convert Pydantic model to dict."""
    return obj.model_dump(mode="json", by_alias=False)


def _dump_many(objs) -> list[dict]:
    """Convert list of Pydantic models to list of dicts."""
    return [_dump(obj) for obj in objs]


def ingest_draft(
    config: IngestionConfig,
    client: SleeperClient | None = None,
    store: DataStore | None = None,
) -> dict[str, int]:
    """Ingest draft data from Sleeper API.

    Args:
        config: Ingestion configuration
        client: Optional SleeperClient (creates new one if not provided)
        store: Optional DataStore (creates new one if not provided)

    Returns:
        Dict with ingestion summary: {
            "drafts_found": int,
            "picks_ingested": int,
            "draft_id": str
        }

    Raises:
        RuntimeError: If no drafts found for league
    """
    # Create client and store if not provided
    should_close_client = client is None
    should_close_store = False  # DataStore doesn't need explicit closing

    if client is None:
        client = SleeperClient()

    if store is None:
        store = DataStore(database_path=config.database_path)

    try:
        logger.info(
            "draft_ingestion_started",
            league_id=config.league_id,
            season=config.season,
        )

        # Fetch drafts for the league
        drafts = client.get_drafts(config.league_id)

        if not drafts:
            raise RuntimeError(f"No drafts found for league {config.league_id}")

        logger.info("drafts_found", count=len(drafts))

        # Use the first (most recent) draft
        draft = drafts[0]
        draft_id = draft["draft_id"]
        draft_type = draft.get("type", "unknown")
        draft_status = draft.get("status", "unknown")

        logger.info(
            "processing_draft",
            draft_id=draft_id,
            type=draft_type,
            status=draft_status,
        )

        # Fetch all picks for this draft
        picks = client.get_draft_picks(draft_id)

        logger.info("draft_picks_fetched", count=len(picks))

        # Save draft picks to database
        store.write_table("draft_picks", _dump_many(picks), mode="replace")

        summary = {
            "drafts_found": len(drafts),
            "picks_ingested": len(picks),
            "draft_id": draft_id,
            "draft_type": draft_type,
            "draft_status": draft_status,
        }

        logger.info(
            "draft_ingestion_completed",
            **summary,
        )

        return summary

    finally:
        if should_close_client and client:
            client.close()


def main():
    """CLI entry point for draft ingestion."""
    config = load_config()

    logger.info("starting_draft_ingestion")

    summary = ingest_draft(config)

    logger.info(
        "draft_ingestion_summary",
        **summary,
    )

    print("\n✅ Draft ingestion completed!")
    print(f"   - Draft ID: {summary['draft_id']}")
    print(f"   - Picks ingested: {summary['picks_ingested']}")
    print(f"   - Draft type: {summary['draft_type']}")
    print(f"   - Status: {summary['draft_status']}")


if __name__ == "__main__":
    main()
