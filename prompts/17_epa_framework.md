# Enhancement: Add Expected Points Added (EPA) Framework

## Background

**Current**: Only actual PPG and total points
**Missing**: Expected points based on opportunity (targets, carries, air yards)

**Why it matters**: Separates skill from luck and predicts regression.

## Example

Two WRs averaging 15 PPG:

- **WR A**: 10 targets/game, 8 catches, 100 air yards → **Efficient** but low volume
- **WR B**: 6 targets/game, 3 catches, 40 air yards + 1 TD → **TD-dependent**, unsustainable

Expected Points framework would flag WR B as regression candidate (TDs are flukey).

## Industry Standards

- **4for4**: Uses "Expected Fantasy Points" based on target share and air yards
- **PFF**: EPA (Expected Points Added) from actual NFL play-by-play
- **The Ringer**: Warren Sharp's "expected TD rate" vs actual TD rate
- **nflfastR**: Open-source EPA data (used by analytics community)

## Data Sources

### Option A: Air Yards (Easier, Free)

- **Source**: airyards.com API or scraping
- **Metrics**: Target share, air yards share, aDOT (average depth of target)
- **Formula**: `Expected PPG = (target_share × team_pass_attempts × yards_per_target) / 10`

### Option B: nflfastR Play-by-Play (Advanced, More Accurate)

- **Source**: nflfastR R package (has Python wrapper: nfl_data_py)
- **Metrics**: EPA, CPOE (Completion % Over Expected), success rate
- **Requires**: More data processing, but gold standard

## Implementation (Start with Air Yards - Simpler)

### Step 1: Add air yards data source

**Option 1: Scrape airyards.com** (free, easier):

**Create `src/ingestion/airyards_scraper.py`:**

```python
"""
Air Yards Scraper

Scrapes target share and air yards data from airyards.com
Note: Be respectful of their servers, cache results
"""

import httpx
from bs4 import BeautifulSoup
import pandas as pd


class AirYardsScraper:
    """Scrape air yards data from airyards.com"""

    BASE_URL = "https://airyards.com/{season}/weeks/1-{week}"

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def get_air_yards(self, season: int = 2025, week: int = 8) -> list[dict]:
        """
        Scrape air yards data for WR/TE

        Returns:
            List of dicts with player air yards metrics
        """
        url = self.BASE_URL.format(season=season, week=week)
        response = self.client.get(url)
        response.raise_for_status()

        # Parse HTML table (structure varies, check current site)
        soup = BeautifulSoup(response.text, 'html.parser')

        # This is a placeholder - inspect airyards.com to get actual table structure
        # They usually have a CSV download button - could also use that

        # Example structure (adjust based on actual site):
        # player_name, team, targets, target_share, air_yards, air_yards_share, adot

        players = []
        # TODO: Implement actual parsing based on site structure

        return players

    def close(self):
        self.client.close()
```

**Option 2: Use nfl_data_py** (more robust):

```bash
# Add to pyproject.toml
poetry add nfl-data-py
```

```python
"""
NFL Data Client using nfl_data_py

Wrapper around nflfastR data (play-by-play, weekly stats)
"""

import nfl_data_py as nfl
import pandas as pd


def get_weekly_stats(season: int, week: int) -> pd.DataFrame:
    """
    Get weekly player stats from nflfastR

    Returns:
        DataFrame with player stats including targets, receptions, yards, TDs
    """
    # nfl_data_py provides weekly stats
    weekly_data = nfl.import_weekly_data([season])

    # Filter to specific week
    week_data = weekly_data[weekly_data['week'] == week]

    return week_data


def get_seasonal_stats(season: int) -> pd.DataFrame:
    """Get season-long aggregated stats"""
    seasonal_data = nfl.import_seasonal_data([season])
    return seasonal_data
```

### Step 2: Create expected points model

**Create `dbt/models/intermediate/int_expected_fantasy_points.sql`:**

```sql
{{ config(materialized='table') }}

/*
Expected Fantasy Points - Opportunity-Based Projections

Methodology:
1. Calculate expected points based on opportunity (targets, carries)
2. Compare to actual points (identify over/underperformers)
3. Flag regression candidates (actual >> expected = lucky, unsustainable)

Based on target share and typical conversion rates.
*/

with player_stats as (
    select * from {{ ref('stg_player_stats') }}
),

-- Get team-level aggregates (for target share calculation)
team_stats as (
    select
        team,
        week,
        sum(case when position in ('WR', 'TE', 'RB') then targets else 0 end) as team_targets,
        sum(case when position = 'RB' then carries else 0 end) as team_carries
    from player_stats
    group by team, week
),

-- Calculate opportunity metrics
opportunity_metrics as (
    select
        ps.player_id,
        ps.player_name,
        ps.position,
        ps.team,
        ps.week,
        ps.weekly_points as actual_points,
        ps.targets,
        ps.receptions,
        ps.receiving_yards,
        ps.receiving_tds,
        ps.carries,
        ps.rushing_yards,
        ps.rushing_tds,

        -- Target share
        case
            when ts.team_targets > 0 and ps.position in ('WR', 'TE')
                then round(ps.targets::double / ts.team_targets, 3)
            else null
        end as target_share,

        -- Carry share
        case
            when ts.team_carries > 0 and ps.position = 'RB'
                then round(ps.carries::double / ts.team_carries, 3)
            else null
        end as carry_share

    from player_stats ps
    left join team_stats ts
        on ps.team = ts.team and ps.week = ts.week
    where ps.position in ('RB', 'WR', 'TE')
),

-- Calculate expected points based on opportunity
expected_points_calc as (
    select
        *,

        -- Expected points from targets (PPR)
        -- League average: ~0.75 PPR points per target (receptions + yards + TDs)
        -- This is a rough estimate - real calculation would use historical conversion rates
        case
            when targets is not null and position in ('WR', 'TE')
                then targets * 0.75
            else 0
        end as expected_points_receiving,

        -- Expected points from carries
        -- League average: ~0.5 points per carry (yards + TDs)
        case
            when carries is not null and position = 'RB'
                then carries * 0.5
            else 0
        end as expected_points_rushing,

        -- TD regression indicator
        -- Expected TDs based on opportunity (red zone touches, etc.)
        -- For now, use league average: ~1 TD per 20 targets or 15 carries
        (coalesce(targets, 0) / 20.0 + coalesce(carries, 0) / 15.0) as expected_tds,
        (coalesce(receiving_tds, 0) + coalesce(rushing_tds, 0)) as actual_tds

    from opportunity_metrics
),

final as (
    select
        player_id,
        player_name,
        position,
        team,
        week,
        actual_points,
        targets,
        target_share,
        carries,
        carry_share,

        -- Expected points
        round(expected_points_receiving + expected_points_rushing, 1) as expected_points,

        -- Points over expected (luck/efficiency)
        round(actual_points - (expected_points_receiving + expected_points_rushing), 1)
            as points_over_expected,

        -- TD regression flag
        expected_tds,
        actual_tds,
        round(actual_tds - expected_tds, 2) as tds_over_expected,

        case
            when actual_tds > expected_tds + 0.5 then 'POSITIVE_REGRESSION_CANDIDATE'
            when actual_tds < expected_tds - 0.5 then 'NEGATIVE_REGRESSION_CANDIDATE'
            else 'NEUTRAL'
        end as regression_flag

    from expected_points_calc
)

select * from final
order by player_name, week
```

### Step 3: Aggregate to season-level regression analysis

**Create `dbt/models/marts/fct_regression_candidates.sql`:**

```sql
{{ config(materialized='table') }}

-- Identify players likely to regress (positive or negative)

with expected_points as (
    select * from {{ ref('int_expected_fantasy_points') }}
),

season_aggregates as (
    select
        player_id,
        player_name,
        position,
        team,
        count(*) as weeks_played,

        -- Actual vs Expected
        round(sum(actual_points), 1) as total_actual_points,
        round(sum(expected_points), 1) as total_expected_points,
        round(sum(points_over_expected), 1) as total_poe,
        round(avg(points_over_expected), 1) as avg_poe_per_game,

        -- TD regression
        round(sum(actual_tds), 1) as total_actual_tds,
        round(sum(expected_tds), 1) as total_expected_tds,
        round(sum(tds_over_expected), 2) as total_td_luck,

        -- Opportunity
        round(avg(target_share), 3) as avg_target_share,
        round(avg(carry_share), 3) as avg_carry_share

    from expected_points
    group by player_id, player_name, position, team
    having count(*) >= 4  -- Minimum 4 games
)

select
    *,

    -- Regression tier
    case
        when total_poe > 20 and total_td_luck > 2
            then 'HIGH_POSITIVE_REGRESSION'  -- Overperforming, likely to decline
        when total_poe > 10
            then 'MODERATE_POSITIVE_REGRESSION'
        when total_poe < -20 and total_td_luck < -2
            then 'HIGH_NEGATIVE_REGRESSION'  -- Underperforming, likely to improve
        when total_poe < -10
            then 'MODERATE_NEGATIVE_REGRESSION'
        else 'STABLE'
    end as regression_tier,

    -- Sell high / buy low recommendation
    case
        when total_poe > 20 then 'SELL HIGH (Overperforming opportunity)'
        when total_poe < -20 then 'BUY LOW (Underperforming opportunity)'
        when avg_target_share >= 0.25 then 'HOLD (Strong opportunity)'
        else 'NEUTRAL'
    end as trade_recommendation

from season_aggregates
order by total_poe desc
```

### Step 4: Add to dashboard

Show regression candidates on ROS or Trade Analyzer page:

```python
# In ROS Rankings page or new "Regression Analysis" section:

st.subheader("🎯 Regression Candidates (Buy Low / Sell High)")

@st.cache_data
def load_regression_candidates(_db_mtime):
    """Load regression analysis"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                player_name,
                position,
                weeks_played,
                total_actual_points,
                total_expected_points,
                total_poe,
                regression_tier,
                trade_recommendation
            FROM main_analytics.fct_regression_candidates
            WHERE regression_tier != 'STABLE'
            ORDER BY abs(total_poe) DESC
            """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load regression analysis: {str(e)}")
        return pd.DataFrame()

regression_df = load_regression_candidates(get_db_mtime())

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📉 Sell High (Positive Regression)")
    sell_high = regression_df[
        regression_df["regression_tier"].str.contains("POSITIVE")
    ]
    st.dataframe(sell_high, hide_index=True)

with col2:
    st.markdown("### 📈 Buy Low (Negative Regression)")
    buy_low = regression_df[
        regression_df["regression_tier"].str.contains("NEGATIVE")
    ]
    st.dataframe(buy_low, hide_index=True)
```

## Task

1. Choose data source (nfl_data_py recommended for simplicity)
2. Install package: `poetry add nfl-data-py`
3. Create `int_expected_fantasy_points.sql` model
4. Create `fct_regression_candidates.sql` mart
5. Add regression analysis section to dashboard
6. Run DBT: `cd dbt && poetry run dbt build`
7. Test dashboard

## Completion Criteria

- [ ] Expected points calculated based on opportunity
- [ ] Regression candidates identified (positive and negative)
- [ ] Dashboard shows buy low / sell high recommendations
- [ ] All tests pass

## Validation

Look for known regression candidates:

- **Positive regression**: Player with 6 TDs in 4 games (unsustainable TD rate)
- **Negative regression**: Player with 25% target share but only 8 PPG (TDs will come)

---

**Note**: This is a simplified implementation. Full EPA framework would require play-by-play data and more sophisticated modeling.

---

**After completing this task:**

1. Mark #17 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 17` (or manually update)
3. Move to prompt #18
