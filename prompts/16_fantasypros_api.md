# Enhancement: Integrate FantasyPros Consensus Projections API

## Background

**Current**: Using preseason ADP as proxy for player projections (decent but not ideal)
**Better**: Actual expert consensus projections from FantasyPros (aggregates 100+ analysts)

FantasyPros provides:

- **Free tier**: 1000 API calls/month (plenty for weekly updates)
- **Consensus rankings**: Aggregated from ESPN, Yahoo, CBS, NFL.com, etc.
- **Projected points**: Weekly and season-long projections
- **Industry standard**: Most platforms use FantasyPros as baseline

## Why This Matters

1. **More accurate draft analysis**: Real projections vs rough ADP estimates
2. **Weekly projections**: Can power ROS rankings, trade analyzer, lineup optimizer
3. **Credibility**: "Powered by FantasyPros Consensus" = industry standard

## Implementation

### Step 1: Sign up for FantasyPros API

1. Go to: <https://www.fantasypros.com/api/>
2. Sign up for **free tier** (1000 calls/month)
3. Get API key
4. Add to `.env`:

   ```
   FANTASYPROS_API_KEY=your_api_key_here
   ```

### Step 2: Add FantasyPros client to ingestion

**Create `src/ingestion/fantasypros_client.py`:**

```python
"""
FantasyPros API Client

Free tier: 1000 API calls/month
Docs: https://www.fantasypros.com/api/docs
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel


class PlayerProjection(BaseModel):
    """Player projection from FantasyPros"""
    player_id: str  # FantasyPros player ID
    player_name: str
    team: str
    position: str
    rank_ecr: int  # Expert Consensus Ranking
    rank_min: int  # Best rank from any expert
    rank_max: int  # Worst rank from any expert
    rank_ave: float  # Average rank
    rank_std: float  # Standard deviation of ranks
    projected_points: float | None = None  # Season projection
    # ... add other fields as needed


class FantasyProsClient:
    """Client for FantasyPros API"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("FANTASYPROS_API_KEY")
        if not self.api_key:
            raise ValueError("FANTASYPROS_API_KEY not found in environment")

        self.base_url = "https://api.fantasypros.com/v2"
        self.client = httpx.Client(timeout=30.0)

    def get_consensus_rankings(
        self,
        *,
        sport: str = "nfl",
        position: str = "all",
        scoring: str = "ppr",
        season: int | None = None,
        week: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get consensus rankings from FantasyPros

        Args:
            sport: "nfl" (default)
            position: "qb", "rb", "wr", "te", "all" (default)
            scoring: "ppr" (default), "half-ppr", "standard"
            season: Season year (default: current season)
            week: Week number for weekly projections (optional)

        Returns:
            List of player rankings/projections
        """
        url = f"{self.base_url}/json/nfl/{season or 2025}/consensus-rankings"

        params = {
            "position": position,
            "scoring": scoring,
        }

        if week:
            params["week"] = week

        headers = {"x-api-key": self.api_key}

        response = self.client.get(url, params=params, headers=headers)
        response.raise_for_status()

        return response.json().get("players", [])

    def get_projections(
        self,
        *,
        position: str = "all",
        season: int | None = None,
        week: int | None = None,
        scoring: str = "ppr",
    ) -> list[dict[str, Any]]:
        """
        Get player projections (includes projected points)

        Args:
            position: "qb", "rb", "wr", "te", "all"
            season: Season year
            week: Week number (optional - if omitted, returns season projections)
            scoring: "ppr", "half-ppr", "standard"

        Returns:
            List of player projections with point totals
        """
        url = f"{self.base_url}/json/nfl/{season or 2025}/projections"

        params = {
            "position": position,
            "scoring": scoring,
        }

        if week:
            params["week"] = week

        headers = {"x-api-key": self.api_key}

        response = self.client.get(url, params=params, headers=headers)
        response.raise_for_status()

        return response.json().get("players", [])

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### Step 3: Create staging model for projections

**Create `dbt/models/staging/stg_fantasypros_projections.sql`:**

```sql
{{ config(materialized='table') }}

-- FantasyPros consensus projections (loaded via ingestion)

select
    player_id as fantasypros_player_id,
    player_name,
    team,
    position,
    rank_ecr as consensus_rank,
    rank_std as ranking_variance,  -- How much experts disagree
    projected_points as season_projection,
    'FantasyPros_Consensus' as projection_source,
    current_timestamp as loaded_at

from {{ source('raw', 'fantasypros_projections') }}
where position in ('QB', 'RB', 'WR', 'TE')
```

### Step 4: Update ingestion to pull projections

Update `src/ingestion/cli.py` to add FantasyPros ingestion:

```python
# Add to imports
from ingestion.fantasypros_client import FantasyProsClient

# Add to run_ingestion function (after Sleeper ingestion)
def run_ingestion(...):
    # ... existing Sleeper ingestion ...

    # Pull FantasyPros projections
    if os.getenv("FANTASYPROS_API_KEY"):
        logger.info("Fetching FantasyPros consensus projections")
        try:
            with FantasyProsClient() as fp_client:
                projections = fp_client.get_projections(
                    season=season,
                    scoring="ppr",  # TODO: Make configurable
                )
                store.write_table("fantasypros_projections", projections)
                logger.info(
                    "FantasyPros projections loaded",
                    count=len(projections)
                )
        except Exception as e:
            logger.error("Failed to load FantasyPros projections", error=str(e))
            # Don't fail the entire ingestion if FantasyPros fails
    else:
        logger.warning("FANTASYPROS_API_KEY not set, skipping projections")
```

### Step 5: Use projections in pick-value curve

Update `dbt/models/intermediate/int_expected_value_by_pick.sql` to use FantasyPros projections instead of hardcoded PPG tiers:

```sql
-- Replace lines 56-103 (preseason_with_projected_ppg CTE) with:

preseason_with_projected_ppg as (
    select
        pr.*,
        rl.estimated_replacement_ppg,
        rl.scarcity_multiplier,

        -- Use FantasyPros projections if available, fallback to ADP-based estimates
        coalesce(
            (
                select season_projection / 17.0  -- Convert to PPG
                from {{ ref('stg_fantasypros_projections') }} fp
                where fp.player_name = pr.player_name
                  and fp.position = pr.position
            ),
            -- Fallback: historical averages (from previous implementation)
            (
                select smoothed_ppg
                from {{ ref('int_historical_ppg_by_rank') }} hpr
                where hpr.position = pr.position
                  and hpr.rank_position = pr.preseason_rank_position
            ),
            -- Last resort: conservative estimate
            case
                when pr.position = 'QB' then 18.0
                when pr.position = 'RB' then 12.0
                when pr.position = 'WR' then 11.0
                when pr.position = 'TE' then 8.0
            end
        ) as projected_ppg

    from preseason_rankings as pr
    left join replacement_levels as rl
        on pr.position = rl.position
)
```

## Task

1. Sign up for FantasyPros API (free tier)
2. Get API key and add to `.env`
3. Create `src/ingestion/fantasypros_client.py`
4. Create `dbt/models/staging/stg_fantasypros_projections.sql`
5. Update `src/ingestion/cli.py` to pull projections
6. Update `int_expected_value_by_pick.sql` to use real projections
7. Run ingestion: `poetry run python -m ingestion.cli`
8. Run DBT: `cd dbt && poetry run dbt build`
9. Verify projections are loaded: `duckdb data/warehouse.duckdb "SELECT COUNT(*) FROM raw.fantasypros_projections"`

## Completion Criteria

- [ ] FantasyPros API key configured in `.env`
- [ ] Client successfully fetches projections
- [ ] Staging model loads projections into DuckDB
- [ ] Pick-value curve uses real projections (not hardcoded tiers)
- [ ] All tests pass

## Validation Query

After implementing, verify projections are loaded:

```sql
SELECT
    player_name,
    position,
    consensus_rank,
    season_projection,
    season_projection / 17.0 as projected_ppg
FROM main_analytics.stg_fantasypros_projections
WHERE position = 'RB'
ORDER BY consensus_rank
LIMIT 10;
```

Expected: Should see top RBs (CMC, Bijan, Breece) with realistic projections (250-300 points).

---

**API Docs**: <https://www.fantasypros.com/api/docs>
**Free Tier Limits**: 1000 calls/month (plenty for weekly updates)
**Cost**: Free for first 1000 calls, then $10/month for next tier

---

**After completing this task:**

1. Mark #16 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 16` (or manually update)
3. Move to prompt #17
