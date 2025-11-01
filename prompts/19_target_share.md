# Enhancement: Add Target Share & Opportunity Metrics

## Background

**Current**: Only PPG and total points (outcome metrics)
**Missing**: **Target share, air yards, red zone usage** (opportunity metrics)

**Why it matters**: Opportunity predicts future performance better than past results.

## Example

Two WRs both averaging 12 PPG:

- **WR A**: 25% team target share, 10 targets/game → Consistent volume, likely to maintain
- **WR B**: 15% target share, 6 targets/game, just scored 2 TDs → TD-dependent, will regress

Target share is a **leading indicator** of future production.

## Industry Standards

- **FantasyPros**: Shows target share % in player profiles
- **4for4**: "Opportunity Score" based on snap %, target share, RZ touches
- **PFF**: Target share, snap share, routes run
- **airyards.com**: Air yards share, aDOT (average depth of target)

## Metrics to Track

### For WR/TE

- **Target Share**: % of team targets
- **Air Yards Share**: % of team air yards (depth of targets)
- **Red Zone Targets**: Targets inside opponent 20-yard line
- **Snap Share**: % of offensive snaps

### For RB

- **Carry Share**: % of team carries
- **Target Share** (pass-catching backs)
- **Red Zone Carries**: Carries inside opponent 20
- **Snap Share**

## Implementation

### Step 1: Extend player stats with opportunity metrics

Update `stg_player_stats.sql` to include opportunity data (if Sleeper API provides it):

```sql
-- Check Sleeper API response for available fields
-- Sleeper provides: targets, receptions, carries
-- May need to add: red_zone_targets, red_zone_carries, snap_share

select
    player_id,
    player_name,
    position,
    team,
    week,

    -- Existing fields
    passing_yards,
    passing_tds,
    interceptions,
    rushing_yards,
    rushing_tds,
    carries,
    receiving_yards,
    receiving_tds,
    targets,
    receptions,

    -- NEW: Opportunity metrics (if available in API)
    -- Note: Sleeper may not provide all of these
    -- Alternative: scrape from Pro Football Reference or use nfl_data_py
    snap_share,
    red_zone_targets,
    red_zone_carries,
    air_yards,  -- Total air yards (yards ball traveled in air)

    -- Calculate PPR points
    (passing_yards * 0.04) + (passing_tds * 4) + (interceptions * -2) +
    (rushing_yards * 0.1) + (rushing_tds * 6) +
    (receptions * 1) + (receiving_yards * 0.1) + (receiving_tds * 6)
        as weekly_points

from {{ source('raw', 'player_stats') }}
```

### Step 2: Calculate team-level aggregates for share metrics

**Create `dbt/models/intermediate/int_opportunity_metrics.sql`:**

```sql
{{ config(materialized='table') }}

/*
Opportunity Metrics - Target Share, Carry Share, Red Zone Usage

Leading indicators of future fantasy production.
*/

with player_stats as (
    select * from {{ ref('stg_player_stats') }}
),

-- Team-level aggregates (for calculating shares)
team_aggregates as (
    select
        team,
        week,
        sum(case when position in ('WR', 'TE', 'RB', 'QB') then targets else 0 end) as team_targets,
        sum(case when position = 'RB' then carries else 0 end) as team_carries,
        sum(case when position in ('WR', 'TE') then coalesce(air_yards, 0) else 0 end) as team_air_yards,
        sum(case when position in ('WR', 'TE', 'RB') then coalesce(red_zone_targets, 0) else 0 end) as team_rz_targets,
        sum(case when position = 'RB' then coalesce(red_zone_carries, 0) else 0 end) as team_rz_carries

    from player_stats
    group by team, week
),

-- Calculate opportunity shares per player
opportunity_shares as (
    select
        ps.player_id,
        ps.player_name,
        ps.position,
        ps.team,
        ps.week,
        ps.weekly_points,
        ps.targets,
        ps.carries,
        ps.red_zone_targets,
        ps.red_zone_carries,
        ps.air_yards,

        -- Target share
        case
            when ta.team_targets > 0 and ps.position in ('WR', 'TE', 'RB')
                then round(ps.targets::double / ta.team_targets, 3)
            else null
        end as target_share,

        -- Carry share (RBs)
        case
            when ta.team_carries > 0 and ps.position = 'RB'
                then round(ps.carries::double / ta.team_carries, 3)
            else null
        end as carry_share,

        -- Air yards share (WR/TE)
        case
            when ta.team_air_yards > 0 and ps.position in ('WR', 'TE')
                then round(coalesce(ps.air_yards, 0)::double / ta.team_air_yards, 3)
            else null
        end as air_yards_share,

        -- Red zone share
        case
            when ta.team_rz_targets > 0 and ps.position in ('WR', 'TE', 'RB')
                then round(coalesce(ps.red_zone_targets, 0)::double / ta.team_rz_targets, 3)
            else null
        end as rz_target_share

    from player_stats ps
    left join team_aggregates ta
        on ps.team = ta.team and ps.week = ta.week
    where ps.position in ('QB', 'RB', 'WR', 'TE')
)

select * from opportunity_shares
order by player_name, week
```

### Step 3: Aggregate to season-level opportunity metrics

**Create `dbt/models/marts/fct_opportunity_analysis.sql`:**

```sql
{{ config(materialized='table') }}

-- Season-long opportunity metrics (for trade analysis and projections)

with opportunity_metrics as (
    select * from {{ ref('int_opportunity_metrics') }}
),

season_aggregates as (
    select
        player_id,
        player_name,
        position,
        team,
        count(*) as weeks_played,

        -- Averages
        round(avg(weekly_points), 2) as avg_ppg,
        round(avg(targets), 1) as avg_targets,
        round(avg(carries), 1) as avg_carries,

        -- Share metrics (season average)
        round(avg(target_share), 3) as avg_target_share,
        round(avg(carry_share), 3) as avg_carry_share,
        round(avg(air_yards_share), 3) as avg_air_yards_share,
        round(avg(rz_target_share), 3) as avg_rz_target_share,

        -- Totals
        sum(targets) as total_targets,
        sum(carries) as total_carries,
        sum(red_zone_targets) as total_rz_targets,
        sum(red_zone_carries) as total_rz_carries

    from opportunity_metrics
    group by player_id, player_name, position, team
    having count(*) >= 4  -- Minimum sample size
)

select
    *,

    -- Opportunity tier (for quick filtering)
    case
        when avg_target_share >= 0.25 or avg_carry_share >= 0.50
            then 'BELLCOW'  -- Elite volume
        when avg_target_share >= 0.18 or avg_carry_share >= 0.35
            then 'HIGH_VOLUME'  -- Strong opportunity
        when avg_target_share >= 0.12 or avg_carry_share >= 0.20
            then 'MODERATE_VOLUME'  -- Decent opportunity
        else 'LOW_VOLUME'  -- Weak opportunity
    end as opportunity_tier,

    -- Red zone usage tier
    case
        when avg_rz_target_share >= 0.20 then 'RZ_ELITE'
        when avg_rz_target_share >= 0.10 then 'RZ_MODERATE'
        else 'RZ_LOW'
    end as rz_usage_tier

from season_aggregates
order by avg_target_share desc nulls last, avg_carry_share desc nulls last
```

### Step 4: Add to dashboard

Show opportunity metrics in Draft Analysis or ROS Rankings:

```python
# Add to ROS Rankings or create new "Opportunity Analysis" section

st.subheader("🎯 Opportunity Metrics (Leading Indicators)")

@st.cache_data
def load_opportunity_metrics(_db_mtime):
    """Load target share and opportunity data"""
    try:
        conn = get_db_connection(_db_mtime)
        return conn.execute(
            """
            SELECT
                player_name,
                position,
                team,
                avg_ppg,
                avg_target_share,
                avg_carry_share,
                avg_rz_target_share,
                opportunity_tier
            FROM main_analytics.fct_opportunity_analysis
            WHERE weeks_played >= 4
            ORDER BY avg_target_share DESC NULLS LAST
            """
        ).df()
    except Exception as e:
        st.error(f"⚠️ Could not load opportunity metrics: {str(e)}")
        return pd.DataFrame()

opportunity_df = load_opportunity_metrics(get_db_mtime())

if not opportunity_df.empty:
    position_filter = st.multiselect(
        "Filter by Position:",
        options=["QB", "RB", "WR", "TE"],
        default=["RB", "WR", "TE"]
    )

    filtered_opp = opportunity_df[
        opportunity_df["position"].isin(position_filter)
    ]

    st.dataframe(
        filtered_opp,
        use_container_width=True,
        hide_index=True,
        column_config={
            "player_name": "Player",
            "position": "Pos",
            "team": "Team",
            "avg_ppg": st.column_config.NumberColumn("PPG", format="%.1f"),
            "avg_target_share": st.column_config.ProgressColumn(
                "Target %",
                format="%.1f%%",
                min_value=0,
                max_value=0.50,
                help="% of team targets (higher = more opportunity)"
            ),
            "avg_carry_share": st.column_config.ProgressColumn(
                "Carry %",
                format="%.1f%%",
                min_value=0,
                max_value=1.0,
                help="% of team carries (RBs only)"
            ),
            "avg_rz_target_share": st.column_config.NumberColumn(
                "RZ %",
                format="%.1f%%",
                help="% of red zone targets (TD upside)"
            ),
            "opportunity_tier": "Tier",
        },
    )

    st.markdown("""
    **💡 How to Use:**
    - **BELLCOW tier** (25%+ target share or 50%+ carry share): Elite volume, highly valuable
    - **HIGH_VOLUME**: Strong opportunity, likely to maintain production
    - **MODERATE_VOLUME**: Decent role, may need TDs to be fantasy relevant
    - **LOW_VOLUME**: Touchdown-dependent, risky for fantasy lineups

    **Red Zone Usage** indicates TD upside (RZ_ELITE = goal-line role).
    """)
```

## Task

1. Check if Sleeper API provides opportunity data (targets, carries exist - check for RZ, snap%, air yards)
2. If not available in Sleeper, add nfl_data_py for opportunity metrics (recommended)
3. Create `int_opportunity_metrics.sql`
4. Create `fct_opportunity_analysis.sql`
5. Add opportunity section to dashboard
6. Run DBT: `cd dbt && poetry run dbt build`
7. Test dashboard

## Completion Criteria

- [ ] Opportunity metrics (target share, carry share) are calculated
- [ ] Dashboard shows opportunity analysis
- [ ] Opportunity tiers (BELLCOW, HIGH_VOLUME, etc.) make sense
- [ ] All tests pass

## Validation Query

```sql
SELECT
    player_name,
    position,
    avg_target_share,
    avg_carry_share,
    opportunity_tier
FROM main_analytics.fct_opportunity_analysis
WHERE position IN ('WR', 'RB')
ORDER BY avg_target_share DESC NULLS LAST
LIMIT 20;
```

Expected: Top WRs/RBs should have 20-30% target share or 40-60% carry share.

---

**Note**: If Sleeper API doesn't provide detailed opportunity data, use **nfl_data_py** to get snap counts, air yards, and red zone usage from nflfastR.

---

**After completing this task:**

1. Mark #19 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 19` (or manually update)
3. Move to prompt #20
