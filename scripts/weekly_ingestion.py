#!/usr/bin/env python3
"""
Weekly ingestion script that auto-detects which week to ingest.

This script:
1. Checks current NFL week from Sleeper API
2. Checks which weeks are already in the database
3. Ingests any missing weeks up to the current completed week
4. Ingests player stats for new weeks
5. Ingests draft data (once per season, idempotent)
6. Runs DBT seed and models to update analytics
"""
import os
import sys
from pathlib import Path

import duckdb
import httpx

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion.cli import main as ingest_main
from ingestion.config import load_config
from ingestion.draft_ingestion import ingest_draft
from ingestion.player_stats_ingestion import ingest_player_stats


def get_current_nfl_week() -> int:
    """Get the current NFL week from Sleeper API."""
    response = httpx.get("https://api.sleeper.app/v1/state/nfl", timeout=10)
    response.raise_for_status()
    state = response.json()

    # The "week" field shows the UPCOMING week during the season
    # We want the most recently COMPLETED week
    current_week = state["week"]

    # If it's early in the week (before Thursday), the previous week just finished
    # This is safer - we'll ingest week N-1 to ensure all games are complete
    completed_week = current_week - 1

    print(f"🏈 Current NFL week: {current_week}")
    print(f"📊 Most recently completed week: {completed_week}")

    return completed_week


def get_ingested_weeks(db_path: str) -> set[int]:
    """Check which weeks are already ingested in the database."""
    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path}, will create new one")
        return set()

    conn = duckdb.connect(db_path, read_only=True)

    try:
        # Check what matchup tables exist
        result = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'staging'
            AND table_name LIKE 'matchups_week_%'
        """
        ).fetchall()

        # Extract week numbers from table names (e.g., 'matchups_week_01' -> 1)
        weeks = set()
        for (table_name,) in result:
            week_str = table_name.replace("matchups_week_", "")
            weeks.add(int(week_str))

        conn.close()
        return weeks
    except Exception as e:
        print(f"⚠️  Error checking database: {e}")
        conn.close()
        return set()


def run_dbt_models():
    """Run DBT seed and models to update analytics after ingestion."""
    import subprocess

    print("\n" + "=" * 80)
    print("🌱 Running DBT seed to load preseason rankings...")
    print("=" * 80)

    dbt_dir = Path(__file__).parent.parent / "dbt"

    try:
        # First run dbt seed to load CSV files (preseason rankings)
        seed_result = subprocess.run(
            ["poetry", "run", "dbt", "seed"],
            cwd=str(dbt_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        print(seed_result.stdout)
        print("✅ DBT seed completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"⚠️  DBT seed failed (non-critical): {e}")
        print(e.stdout)
        print(e.stderr)
        # Don't raise - seed failures are non-critical

    print("\n" + "=" * 80)
    print("🔧 Running DBT models to update analytics...")
    print("=" * 80)

    try:
        # Run DBT from the dbt directory
        result = subprocess.run(
            ["poetry", "run", "dbt", "run"],
            cwd=str(dbt_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        print("✅ DBT models updated successfully!")

    except subprocess.CalledProcessError as e:
        print(f"❌ DBT run failed: {e}")
        print(e.stdout)
        print(e.stderr)
        raise


def main():
    """Main ingestion workflow."""
    print("=" * 80)
    print("🏈 WEEKLY FANTASY FOOTBALL DATA INGESTION")
    print("=" * 80)

    # Get database path from environment
    db_path = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")

    # Determine which week to ingest
    completed_week = get_current_nfl_week()
    ingested_weeks = get_ingested_weeks(db_path)

    print(
        f"\n📋 Already ingested weeks: {sorted(ingested_weeks) if ingested_weeks else 'None'}"
    )

    # Find weeks we need to ingest (1 to completed_week, excluding already ingested)
    weeks_to_ingest = []
    for week in range(1, completed_week + 1):
        if week not in ingested_weeks:
            weeks_to_ingest.append(week)

    if not weeks_to_ingest:
        print(f"\n✅ All weeks up to week {completed_week} are already ingested!")
        print("Nothing to do. Exiting.")
        return 0

    print(f"\n🔄 Weeks to ingest: {weeks_to_ingest}")

    # Ingest each missing week (matchups, rosters, etc.)
    success = True
    for week in weeks_to_ingest:
        print(f"\n{'=' * 80}")
        print(f"📥 Ingesting Week {week}...")
        print("=" * 80)

        try:
            # Call the CLI main function with week argument
            sys.argv = ["ingestion", "--week", str(week)]
            ingest_main()
            print(f"✅ Week {week} ingested successfully!")
        except Exception as e:
            print(f"❌ Failed to ingest week {week}: {e}")
            success = False
            # Continue with other weeks even if one fails

    # Ingest player stats for new weeks
    if weeks_to_ingest and success:
        print(f"\n{'=' * 80}")
        print(f"📊 Ingesting player stats for weeks {weeks_to_ingest}...")
        print("=" * 80)

        try:
            config = load_config()
            stats_summary = ingest_player_stats(config, weeks_to_ingest)
            print(f"✅ Player stats ingested successfully!")
            print(f"   - Weeks processed: {stats_summary['weeks_processed']}")
            print(f"   - Total player-week records: {stats_summary['total_player_stats']}")
        except Exception as e:
            print(f"⚠️  Failed to ingest player stats (non-critical): {e}")
            # Don't set success = False - player stats are supplementary

    # Ingest draft data (idempotent, safe to re-run)
    print(f"\n{'=' * 80}")
    print("🏈 Ingesting draft data...")
    print("=" * 80)

    try:
        config = load_config()
        draft_summary = ingest_draft(config)
        print(f"✅ Draft data ingested successfully!")
        print(f"   - Draft ID: {draft_summary['draft_id']}")
        print(f"   - Picks: {draft_summary['picks_ingested']}")
    except Exception as e:
        print(f"⚠️  Failed to ingest draft data (non-critical): {e}")
        # Don't set success = False - draft data is supplementary

    # Run DBT to update analytics
    if success:
        try:
            run_dbt_models()
        except Exception as e:
            print(f"❌ DBT run failed: {e}")
            return 1

    print("\n" + "=" * 80)
    print("🎉 INGESTION COMPLETE!")
    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
