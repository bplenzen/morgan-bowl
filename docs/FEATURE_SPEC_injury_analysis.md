# Feature Specification: Injury Impact & Bad Luck Analysis

## Overview

Quantify how injuries have affected each team in the Morgan Bowl league and create a "Bad Luck Rankings" report that shows which teams have been most unlucky with player injuries.

## Business Value

- **High Engagement**: Everyone wants to complain about injuries - give them data to back it up!
- **Competitive Insight**: Understand if a team is struggling due to skill or bad luck
- **Entertainment**: "Who's the unluckiest manager?" is a fun debate
- **Historical Context**: Track injury patterns across the season

## Data Requirements

### New Data Sources Needed

1. **Player Injury Status** (Sleeper API)
   - Endpoint: `GET /v1/league/{league_id}/rosters/{week}`
   - Fields needed:
     - `player_id`
     - `status` (IR, Out, Doubtful, Questionable, Probable)
     - `injury` (injury type/body part)

2. **Player Weekly Stats** (Sleeper API)
   - Endpoint: `GET /v1/stats/nfl/regular/{season}/{week}`
   - Fields needed:
     - `player_id`
     - `pts_ppr` (or pts_half_ppr depending on league)
     - `gp` (games played)

3. **Draft Data** (Sleeper API)
   - Endpoint: `GET /v1/draft/{draft_id}`
   - Fields needed:
     - `player_id`
     - `draft_slot` (1.01, 1.02, etc.)
     - `round`
     - `pick_no`
     - `roster_id` (which team drafted them)

4. **Player Metadata** (Sleeper API)
   - Endpoint: `GET /v1/players/nfl`
   - Fields needed:
     - `player_id`
     - `full_name`
     - `position`
     - `team`

## Data Models

### Staging Layer

#### `stg_player_injuries.sql`

```sql
-- Staging model for player injury data
with raw_rosters as (
    select * from {{ source('sleeper', 'rosters') }}
),

player_weeks as (
    select
        roster_id,
        week,
        player_id,
        status,
        injury_type,
        -- Injury severity weighting
        case
            when status = 'IR' then 4
            when status = 'Out' then 3
            when status = 'Doubtful' then 2
            when status = 'Questionable' then 1
            else 0
        end as injury_severity_weight
    from raw_rosters
    cross join unnest(players) as player_id
    where status in ('IR', 'Out', 'Doubtful', 'Questionable')
)

select * from player_weeks
```

#### `stg_player_weekly_stats.sql`

```sql
-- Staging model for player weekly performance
select
    player_id,
    week,
    season,
    points_ppr,
    games_played,
    -- Calculate season average up to this point
    avg(points_ppr) over (
        partition by player_id, season
        order by week
        rows between unbounded preceding and 1 preceding
    ) as season_avg_points
from {{ source('sleeper', 'player_stats') }}
```

#### `stg_draft_picks.sql`

```sql
-- Staging model for draft data
select
    draft_id,
    pick_no,
    round,
    draft_slot,
    player_id,
    roster_id,
    -- Calculate ADP value (higher pick = more value)
    case
        when pick_no <= 12 then 5  -- Round 1
        when pick_no <= 24 then 4  -- Round 2
        when pick_no <= 36 then 3  -- Round 3
        when pick_no <= 60 then 2  -- Rounds 4-5
        else 1                      -- Later rounds
    end as draft_capital_weight
from {{ source('sleeper', 'draft_picks') }}
```

### Marts Layer

#### `fct_injury_impact.sql`

```sql
-- Fact table for injury impact per team
with injuries as (
    select * from {{ ref('stg_player_injuries') }}
),

player_stats as (
    select * from {{ ref('stg_player_weekly_stats') }}
),

draft_picks as (
    select * from {{ ref('stg_draft_picks') }}
),

injury_impact as (
    select
        i.roster_id,
        i.player_id,
        p.full_name,
        p.position,
        i.week,
        i.status,
        i.injury_type,
        i.injury_severity_weight,

        -- Games missed
        1 as games_missed,

        -- Points lost (use season average)
        coalesce(s.season_avg_points, 0) as projected_points_lost,

        -- Draft capital lost
        d.draft_capital_weight,
        d.pick_no as draft_position,

        -- Composite injury impact score
        (i.injury_severity_weight *
         coalesce(s.season_avg_points, 0) *
         coalesce(d.draft_capital_weight, 1)) as injury_impact_score

    from injuries i
    left join player_stats s
        on i.player_id = s.player_id
        and i.week = s.week
    left join draft_picks d
        on i.player_id = d.player_id
    left join {{ ref('stg_players') }} p
        on i.player_id = p.player_id
)

select
    roster_id,
    player_id,
    full_name,
    position,
    week,
    status,
    injury_type,
    games_missed,
    projected_points_lost,
    draft_position,
    draft_capital_weight,
    injury_impact_score
from injury_impact
```

#### `fct_bad_luck_rankings.sql`

```sql
-- Team-level bad luck rankings
with injury_impact as (
    select * from {{ ref('fct_injury_impact') }}
),

team_injury_summary as (
    select
        i.roster_id,
        u.display_name as manager_name,

        -- Count metrics
        count(distinct i.player_id) as unique_players_injured,
        count(*) as total_injury_weeks,
        sum(i.games_missed) as total_games_missed,

        -- Points metrics
        sum(i.projected_points_lost) as total_points_lost,
        avg(i.projected_points_lost) as avg_points_lost_per_injury,

        -- Draft capital metrics
        sum(i.draft_capital_weight) as total_draft_capital_lost,
        avg(i.draft_position) as avg_draft_position_injured,

        -- Composite bad luck score
        sum(i.injury_impact_score) as bad_luck_index,

        -- Breakdown by injury severity
        sum(case when i.status = 'IR' then 1 else 0 end) as ir_injuries,
        sum(case when i.status = 'Out' then 1 else 0 end) as out_injuries,
        sum(case when i.status = 'Doubtful' then 1 else 0 end) as doubtful_injuries,

        -- Top injured player
        max(i.projected_points_lost) as worst_single_injury_impact

    from injury_impact i
    left join {{ ref('stg_users') }} u on i.roster_id = u.roster_id
    group by i.roster_id, u.display_name
)

select
    *,
    -- Rank teams by bad luck (1 = unluckiest)
    row_number() over (order by bad_luck_index desc) as bad_luck_rank,

    -- Percentile ranking
    percent_rank() over (order by bad_luck_index) as bad_luck_percentile

from team_injury_summary
order by bad_luck_index desc
```

## Metrics Explained

### 1. Games Missed

Simple count of player-weeks where a player was injured and didn't play.

### 2. Projected Points Lost

For each injury week, estimate points the team missed out on:

- Use player's season average PPG (up to that point)
- If player hasn't played enough, use position average
- Formula: `SUM(season_avg_points)` across all injury weeks

### 3. Draft Capital Lost

Weight injuries by where the player was drafted:

- Round 1 picks = 5 points
- Round 2 picks = 4 points
- Round 3 picks = 3 points
- Rounds 4-5 = 2 points
- Later rounds = 1 point

Rationale: Losing Ja'Marr Chase (1.01) to injury is worse than losing a waiver pickup.

### 4. Injury Impact Score

Composite score combining:

- **Injury Severity** (IR=4, Out=3, Doubtful=2, Questionable=1)
- **Projected Points Lost** (player's average)
- **Draft Capital Weight** (draft position value)

Formula: `injury_severity * projected_points * draft_capital`

### 5. Bad Luck Index

Team-level sum of all injury impact scores across the season.

- Higher score = unluckier team
- Used to rank teams from most to least unlucky

## Report Output

### Weekly Report Section

```markdown
## 🚑 Injury Impact Report - Week 6

### Most Unlucky Team This Week
**Ben's Team** - 45.2 injury impact points
- Ja'Marr Chase (Out) - 18.5 projected points lost
- Christian McCaffrey (IR) - 22.1 projected points lost
- Total: 40.6 points lost to injuries

### Season Bad Luck Rankings

| Rank | Manager | Bad Luck Index | Games Missed | Points Lost | IR Injuries |
|------|---------|----------------|--------------|-------------|-------------|
| 1    | Ben     | 487.3          | 15           | 212.5       | 3           |
| 2    | Sarah   | 423.1          | 12           | 189.3       | 2           |
| 3    | Mike    | 381.7          | 11           | 165.8       | 2           |
| 4    | Jess    | 245.2          | 8            | 98.4        | 1           |
| 5    | Tom     | 189.5          | 6            | 72.1        | 0           |
| 6    | Alex    | 142.8          | 5            | 54.3        | 1           |

### Top 3 Most Impactful Injuries (Season)
1. **Ben - Ja'Marr Chase** (Draft: 1.01) - 125.4 impact score
2. **Sarah - Christian McCaffrey** (Draft: 1.02) - 118.7 impact score
3. **Mike - Justin Jefferson** (Draft: 1.04) - 97.3 impact score
```

## Dashboard Visualizations

1. **Bad Luck Index Line Chart**
   - X-axis: Week
   - Y-axis: Cumulative bad luck index
   - Line per team
   - Shows who's getting more unlucky over time

2. **Injury Heatmap**
   - Rows: Teams
   - Columns: Weeks
   - Color: Injury impact score (red = worse)
   - Hover: Player names + injury

3. **Draft Capital Lost Bar Chart**
   - X-axis: Teams
   - Y-axis: Total draft capital lost
   - Stacked by round (Round 1 = darkest)

## Implementation Checklist

- [ ] Add Sleeper API endpoints for injury data
- [ ] Create `stg_player_injuries.sql` staging model
- [ ] Create `stg_player_weekly_stats.sql` staging model
- [ ] Create `stg_draft_picks.sql` staging model
- [ ] Create `fct_injury_impact.sql` mart model
- [ ] Create `fct_bad_luck_rankings.sql` mart model
- [ ] Add DBT tests for data quality
- [ ] Update `scripts/generate_report.py` with injury section
- [ ] Add injury visualizations to dashboard
- [ ] Test with real league data

## Future Enhancements

1. **Injury Prediction**: Use historical data to predict which teams are at highest injury risk
2. **Position Scarcity**: Weight RB injuries higher than WR (scarcity adjustment)
3. **Playoff Impact**: Show how injuries affected playoff seeding
4. **Year-over-Year**: Compare injury luck across multiple seasons
5. **"What If" Analysis**: "What if Ben's team had no injuries? What would their record be?"

## Questions to Answer

1. Do we count "Questionable" tags that played anyway?
   - **Proposed**: No, only count injuries where player missed games
2. How do we handle players traded mid-season?
   - **Proposed**: Credit injury to team that owned them during injury
3. What about players dropped before getting injured?
   - **Proposed**: Don't count injuries for players not on your roster

---

**Estimated Effort**: 6-8 hours
**Priority**: HIGH - Do after critical fixes
**Dependencies**: Need Sleeper API endpoints for injury + draft data
