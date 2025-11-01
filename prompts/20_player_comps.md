# Enhancement: Add Player Similarity Scores ("Comparables")

## Background

**Concept**: "This player's profile is 87% similar to 2018 Davante Adams"

**Why it matters**: Helps identify:

- **Breakout candidates**: Similar to past breakouts
- **Regression candidates**: Similar to past busts
- **Trade targets**: Find undervalued similar players

## Industry Standards

- **ESPN Player Comparisons**: Shows historical comps
- **Bill Barnwell's "Comparables"**: Annual column comparing current players to historical seasons
- **FantasyPros "Similar Players"**: Algorithm-based similarity scores

## Implementation Approach

Use **k-Nearest Neighbors (KNN)** or **cosine similarity** to find players with similar statistical profiles.

### Features to Compare

- Age
- Target share / Carry share
- Yards per target / Yards per carry
- TD rate
- Games played (availability)
- Positional rank
- Volatility (coefficient of variation)

### Step 1: Create historical player profile dataset

**Note**: This requires historical data from previous seasons. If you don't have it, start with current season only.

**Create `dbt/models/intermediate/int_player_similarity_profiles.sql`:**

```sql
{{ config(materialized='table') }}

/*
Player Similarity Profiles

Creates feature vectors for each player to enable similarity comparisons.
Uses standardized metrics for fair comparison across positions.
*/

with current_rankings as (
    select * from {{ ref('int_current_player_rankings') }}
),

variance_metrics as (
    select * from {{ ref('int_player_weekly_variance') }}
),

opportunity_metrics as (
    select * from {{ ref('fct_opportunity_analysis') }}
),

-- Create normalized feature vectors
player_profiles as (
    select
        cr.player_id,
        cr.player_name,
        cr.position,
        cr.team,
        2025 as season,  -- Hardcode current season for now

        -- Core stats (normalized)
        cr.points_per_game,
        cr.current_rank_position,
        cr.games_played,

        -- Opportunity metrics
        om.avg_target_share,
        om.avg_carry_share,
        om.avg_rz_target_share,

        -- Efficiency metrics
        case
            when om.total_targets > 0
                then cr.total_points / om.total_targets  -- Points per target
        end as points_per_target,

        case
            when om.total_carries > 0
                then cr.total_points / om.total_carries  -- Points per carry
        end as points_per_carry,

        -- Consistency metrics
        vm.coefficient_of_variation,
        vm.boom_rate_pct,
        vm.bust_rate_pct,
        vm.spike_week_rate_pct,

        -- Age (if available - may need to add to data model)
        -- For now, omit age or hardcode estimates
        null as age

    from current_rankings cr
    left join variance_metrics vm on cr.player_id = vm.player_id
    left join opportunity_metrics om on cr.player_id = om.player_id
    where cr.games_played >= 4  -- Minimum sample size
)

select
    *,

    -- Standardize features for similarity calculations
    -- (z-score normalization: (value - mean) / stddev)
    round(
        (points_per_game - avg(points_per_game) over (partition by position)) /
        nullif(stddev(points_per_game) over (partition by position), 0),
        3
    ) as ppg_zscore,

    round(
        (coefficient_of_variation - avg(coefficient_of_variation) over (partition by position)) /
        nullif(stddev(coefficient_of_variation) over (partition by position), 0),
        3
    ) as cv_zscore,

    round(
        (coalesce(avg_target_share, 0) - avg(coalesce(avg_target_share, 0)) over (partition by position)) /
        nullif(stddev(coalesce(avg_target_share, 0)) over (partition by position), 0),
        3
    ) as target_share_zscore

from player_profiles
```

### Step 2: Calculate pairwise similarity scores

**Create `dbt/models/marts/fct_player_similarity.sql`:**

```sql
{{ config(materialized='table') }}

/*
Player Similarity Scores

Finds the most similar players using Euclidean distance in normalized feature space.

NOTE: This is computationally expensive (N^2 comparisons).
For large datasets, use Python/scikit-learn instead.
*/

with profiles as (
    select * from {{ ref('int_player_similarity_profiles') }}
),

-- Calculate pairwise distances (within same position)
similarity_scores as (
    select
        p1.player_id as player_id,
        p1.player_name as player_name,
        p1.position,
        p2.player_id as comp_player_id,
        p2.player_name as comp_player_name,
        p2.season as comp_season,

        -- Euclidean distance in normalized feature space
        -- Lower distance = more similar
        round(
            sqrt(
                power(coalesce(p1.ppg_zscore, 0) - coalesce(p2.ppg_zscore, 0), 2) +
                power(coalesce(p1.cv_zscore, 0) - coalesce(p2.cv_zscore, 0), 2) +
                power(coalesce(p1.target_share_zscore, 0) - coalesce(p2.target_share_zscore, 0), 2)
                -- Add more features as needed
            ),
            3
        ) as distance,

        -- Convert to similarity score (0-100)
        round(
            100 / (1 + sqrt(
                power(coalesce(p1.ppg_zscore, 0) - coalesce(p2.ppg_zscore, 0), 2) +
                power(coalesce(p1.cv_zscore, 0) - coalesce(p2.cv_zscore, 0), 2) +
                power(coalesce(p1.target_share_zscore, 0) - coalesce(p2.target_share_zscore, 0), 2)
            )),
            1
        ) as similarity_score

    from profiles p1
    cross join profiles p2
    where p1.player_id != p2.player_id  -- Don't compare player to themselves
      and p1.position = p2.position     -- Same position only
),

-- Rank by similarity
ranked_comps as (
    select
        *,
        row_number() over (
            partition by player_id
            order by similarity_score desc
        ) as similarity_rank

    from similarity_scores
)

select * from ranked_comps
where similarity_rank <= 5  -- Keep top 5 comps per player
order by player_id, similarity_rank
```

### Step 3: Add to dashboard

Show player comps in Draft Analysis or ROS Rankings:

```python
# Add to Draft Analysis or create new "Player Comparisons" section

st.subheader("🔍 Player Comparisons (Who are they similar to?)")

player_search = st.selectbox(
    "Search for a player:",
    options=sorted(draft_df["player_name"].unique())
)

if player_search:
    @st.cache_data
    def load_player_comps(_db_mtime, player_name):
        """Load similar players"""
        try:
            conn = get_db_connection(_db_mtime)
            return conn.execute(
                f"""
                SELECT
                    comp_player_name,
                    comp_season,
                    similarity_score,
                    similarity_rank
                FROM main_analytics.fct_player_similarity
                WHERE player_name = '{player_name}'
                ORDER BY similarity_rank
                """
            ).df()
        except Exception as e:
            st.error(f"⚠️ Could not load comps: {str(e)}")
            return pd.DataFrame()

    comps_df = load_player_comps(get_db_mtime(), player_search)

    if not comps_df.empty:
        st.markdown(f"**Players similar to {player_search}:**")

        st.dataframe(
            comps_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "comp_player_name": "Similar Player",
                "comp_season": "Season",
                "similarity_score": st.column_config.ProgressColumn(
                    "Similarity",
                    format="%.0f%%",
                    min_value=0,
                    max_value=100,
                ),
                "similarity_rank": "#",
            },
        )

        st.markdown("""
        **💡 How to use:**
        - **High similarity (80%+)**: Very similar profile, study their trajectory
        - **Breakout comps**: Did similar players break out next season?
        - **Regression comps**: Did similar players regress after big year?
        """)
    else:
        st.info("No similar players found (need more historical data)")
```

## Alternative: Use scikit-learn (Better for Large Datasets)

If you have many seasons of historical data, use Python for similarity:

**Create `scripts/calculate_player_similarity.py`:**

```python
"""
Calculate player similarity using scikit-learn

More efficient than SQL for large datasets.
"""

import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import duckdb

# Load player profiles
conn = duckdb.connect("data/warehouse.duckdb")
profiles_df = conn.execute("""
    SELECT
        player_id,
        player_name,
        position,
        season,
        points_per_game,
        coefficient_of_variation,
        avg_target_share,
        avg_carry_share
    FROM main_analytics.int_player_similarity_profiles
""").df()

# Features for similarity
features = [
    "points_per_game",
    "coefficient_of_variation",
    "avg_target_share",
    "avg_carry_share",
]

# Fill NaN and standardize
X = profiles_df[features].fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Find 5 nearest neighbors per player
nbrs = NearestNeighbors(n_neighbors=6, algorithm='auto').fit(X_scaled)
distances, indices = nbrs.kneighbors(X_scaled)

# Create similarity table
similarity_rows = []
for i, row in profiles_df.iterrows():
    for rank, (dist, idx) in enumerate(zip(distances[i][1:], indices[i][1:]), 1):
        # Skip self (first neighbor)
        similarity_rows.append({
            "player_id": row["player_id"],
            "player_name": row["player_name"],
            "position": row["position"],
            "comp_player_id": profiles_df.iloc[idx]["player_id"],
            "comp_player_name": profiles_df.iloc[idx]["player_name"],
            "comp_season": profiles_df.iloc[idx]["season"],
            "similarity_score": round(100 / (1 + dist), 1),
            "similarity_rank": rank,
        })

similarity_df = pd.DataFrame(similarity_rows)

# Write back to DuckDB
conn.execute("CREATE OR REPLACE TABLE main_analytics.fct_player_similarity AS SELECT * FROM similarity_df")
print(f"✅ Calculated similarity for {len(profiles_df)} players")
```

Run after DBT build:

```bash
poetry run python scripts/calculate_player_similarity.py
```

## Task

1. Create `int_player_similarity_profiles.sql`
2. Create `fct_player_similarity.sql` (or use Python script)
3. Add player comparison section to dashboard
4. Run DBT: `cd dbt && poetry run dbt build`
5. (Optional) Run Python similarity script for better performance
6. Test dashboard

## Completion Criteria

- [ ] Player similarity profiles are created
- [ ] Top 5 comps are calculated per player
- [ ] Dashboard shows similar players
- [ ] All tests pass

## Validation

Search for a known player archetype:

- **Davante Adams**: Should comp to other high-target-share WRs
- **Derrick Henry**: Should comp to high-carry, low-target RBs
- **Travis Kelce**: Should comp to other elite TEs

---

**Note**: This is a basic implementation. For production, add:

- Historical data from multiple seasons
- More sophisticated features (age, athleticism, team offense)
- Trajectory analysis (did comps break out/regress?)

---

**After completing this task:**

1. Mark #20 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 20` (or manually update)
3. Move to prompt #21
