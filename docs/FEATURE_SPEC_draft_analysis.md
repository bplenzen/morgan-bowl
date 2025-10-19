# Feature Specification: Draft Performance Analysis

## Overview

Analyze how each team's draft picks are performing relative to their draft position and current player rankings. Identify "steals" (players outperforming ADP) and "busts" (players underperforming).

## Business Value

- **Draft Accountability**: See who nailed their draft and who whiffed
- **Entertainment**: Endless roasting material for bad picks
- **Learning**: Identify patterns in successful vs unsuccessful drafts
- **Historical Context**: Track draft performance week-by-week

## User Stories

1. **As a league member**, I want to see if Ja'Marr Chase at 1.01 was worth it compared to other players available
2. **As a league member**, I want to know which round I hit/missed on the most
3. **As a league member**, I want a "Draft Grade" report card for my team
4. **As a league member**, I want to see the biggest steals and busts league-wide

## Data Requirements

### New Data Sources Needed

1. **Draft Data** (Sleeper API)
   - Endpoint: `GET /v1/draft/{draft_id}`
   - Fields:
     - `player_id`
     - `draft_slot` (formatted as "1.01", "1.02", etc.)
     - `round`
     - `pick_no` (overall pick number)
     - `roster_id`

2. **Current Player Rankings** (External API)
   - **Option 1**: FantasyPros API
     - Endpoint: `https://api.fantasypros.com/v2/json/nfl/{year}/consensus-rankings`
     - Need: Overall rank, position rank, points scored
   - **Option 2**: Sleeper Player Stats (simpler)
     - Use season total points to calculate rankings
     - Pro: No external API needed
     - Con: Rankings based on points only, not expert consensus

3. **Player Season Stats** (Sleeper API)
   - Endpoint: `GET /v1/stats/nfl/regular/{season}`
   - Fields:
     - `player_id`
     - `pts_ppr` (season total)
     - `gp` (games played)

## Data Models

### Staging Layer

#### `stg_draft_picks.sql`

```sql
-- Staging model for draft results
with raw_draft as (
    select * from {{ source('sleeper', 'draft_picks') }}
),

formatted_picks as (
    select
        draft_id,
        player_id,
        roster_id,
        round,
        pick_no,

        -- Format draft slot as "1.01", "2.03", etc.
        concat(
            round,
            '.',
            lpad((pick_no - ((round - 1) * {{ var('league_size', 6) }}))::text, 2, '0')
        ) as draft_slot,

        -- Calculate expected value based on draft position
        -- Earlier picks = higher expectations
        case
            when pick_no <= 6 then 'Elite (Top 6)'
            when pick_no <= 12 then 'First Round'
            when pick_no <= 24 then 'Second Round'
            when pick_no <= 36 then 'Third Round'
            when pick_no <= 60 then 'Mid Round (4-5)'
            else 'Late Round (6+)'
        end as draft_tier,

        -- Expected points based on draft position (to calculate vs actual)
        case
            when pick_no <= 6 then 250
            when pick_no <= 12 then 220
            when pick_no <= 24 then 180
            when pick_no <= 36 then 150
            when pick_no <= 60 then 120
            else 90
        end as expected_season_points

    from raw_draft
)

select * from formatted_picks
```

#### `stg_player_rankings.sql`

```sql
-- Staging model for current player rankings
-- Option A: Using Sleeper stats to calculate rankings
with player_stats as (
    select
        player_id,
        sum(pts_ppr) as season_points,
        sum(gp) as games_played,
        sum(pts_ppr) / nullif(sum(gp), 0) as points_per_game
    from {{ source('sleeper', 'player_stats') }}
    where season = {{ var('current_season', 2025) }}
    group by player_id
),

player_info as (
    select
        player_id,
        full_name,
        position,
        team
    from {{ ref('stg_players') }}
),

ranked_players as (
    select
        s.player_id,
        p.full_name,
        p.position,
        p.team,
        s.season_points,
        s.games_played,
        s.points_per_game,

        -- Overall rank (across all positions)
        row_number() over (order by s.season_points desc) as overall_rank,

        -- Position rank
        row_number() over (
            partition by p.position
            order by s.season_points desc
        ) as position_rank,

        -- Position tier
        case p.position
            when 'QB' then
                case
                    when row_number() over (partition by p.position order by s.season_points desc) <= 3 then 'QB1 (Elite)'
                    when row_number() over (partition by p.position order by s.season_points desc) <= 12 then 'QB1'
                    else 'QB2+'
                end
            when 'RB' then
                case
                    when row_number() over (partition by p.position order by s.season_points desc) <= 6 then 'RB1 (Elite)'
                    when row_number() over (partition by p.position order by s.season_points desc) <= 24 then 'RB1/RB2'
                    else 'RB3+'
                end
            when 'WR' then
                case
                    when row_number() over (partition by p.position order by s.season_points desc) <= 6 then 'WR1 (Elite)'
                    when row_number() over (partition by p.position order by s.season_points desc) <= 24 then 'WR1/WR2'
                    else 'WR3+'
                end
            when 'TE' then
                case
                    when row_number() over (partition by p.position order by s.season_points desc) <= 3 then 'TE1 (Elite)'
                    when row_number() over (partition by p.position order by s.season_points desc) <= 12 then 'TE1'
                    else 'TE2+'
                end
            else 'Unknown'
        end as position_tier

    from player_stats s
    join player_info p on s.player_id = p.player_id
)

select * from ranked_players
```

### Marts Layer

#### `fct_draft_analysis.sql`

```sql
-- Fact table for draft pick performance
with draft_picks as (
    select * from {{ ref('stg_draft_picks') }}
),

player_rankings as (
    select * from {{ ref('stg_player_rankings') }}
),

draft_performance as (
    select
        d.roster_id,
        u.display_name as manager_name,
        d.player_id,
        r.full_name as player_name,
        r.position,
        r.team,
        d.round,
        d.pick_no,
        d.draft_slot,
        d.draft_tier,
        d.expected_season_points,

        -- Current performance
        coalesce(r.season_points, 0) as actual_season_points,
        coalesce(r.overall_rank, 999) as current_overall_rank,
        coalesce(r.position_rank, 99) as current_position_rank,
        r.position_tier as current_position_tier,
        r.points_per_game,

        -- Value calculations
        (coalesce(r.season_points, 0) - d.expected_season_points) as points_vs_expectation,

        -- Draft position vs current rank difference
        -- Negative = player performing better than draft slot
        (coalesce(r.overall_rank, 999) - d.pick_no) as rank_vs_draft_slot,

        -- Hit/Miss classification
        case
            when coalesce(r.overall_rank, 999) <= d.pick_no - 10 then 'Major Hit (Steal)'
            when coalesce(r.overall_rank, 999) <= d.pick_no then 'Hit'
            when coalesce(r.overall_rank, 999) <= d.pick_no + 10 then 'Fair'
            when coalesce(r.overall_rank, 999) <= d.pick_no + 20 then 'Miss'
            else 'Major Miss (Bust)'
        end as pick_classification,

        -- Value score (negative = good, positive = bad)
        -- Player drafted at 10 but currently ranked 30 = +20 (bad)
        -- Player drafted at 30 but currently ranked 10 = -20 (good, steal!)
        (coalesce(r.overall_rank, 999) - d.pick_no) as pick_value_score

    from draft_picks d
    left join player_rankings r on d.player_id = r.player_id
    left join {{ ref('stg_users') }} u on d.roster_id = u.roster_id
)

select * from draft_performance
order by roster_id, pick_no
```

#### `fct_draft_grades.sql`

```sql
-- Manager-level draft grades
with draft_performance as (
    select * from {{ ref('fct_draft_analysis') }}
),

manager_draft_summary as (
    select
        roster_id,
        manager_name,

        -- Count metrics
        count(*) as total_picks,
        count(case when pick_classification in ('Hit', 'Major Hit (Steal)') then 1 end) as hits,
        count(case when pick_classification in ('Miss', 'Major Miss (Bust)') then 1 end) as misses,
        count(case when pick_classification = 'Fair' then 1 end) as fair_picks,

        -- Best/worst picks
        max(case when pick_value_score = (select min(pick_value_score) from draft_performance dp2 where dp2.roster_id = draft_performance.roster_id)
            then player_name || ' (' || draft_slot || ')' end) as best_pick,
        max(case when pick_value_score = (select max(pick_value_score) from draft_performance dp2 where dp2.roster_id = draft_performance.roster_id)
            then player_name || ' (' || draft_slot || ')' end) as worst_pick,

        -- Points metrics
        sum(actual_season_points) as total_points_from_draft,
        sum(expected_season_points) as total_expected_points,
        sum(points_vs_expectation) as total_points_vs_expectation,
        avg(points_vs_expectation) as avg_points_vs_expectation,

        -- Value metrics
        sum(pick_value_score) as total_draft_value_score,
        avg(pick_value_score) as avg_pick_value_score,

        -- Round-by-round performance
        sum(case when round = 1 then pick_value_score else 0 end) as round_1_value,
        sum(case when round = 2 then pick_value_score else 0 end) as round_2_value,
        sum(case when round = 3 then pick_value_score else 0 end) as round_3_value,
        sum(case when round >= 4 then pick_value_score else 0 end) as late_round_value

    from draft_performance
    group by roster_id, manager_name
)

select
    *,

    -- Calculate draft grade (A-F)
    case
        when avg_pick_value_score <= -15 then 'A+ (Elite Draft)'
        when avg_pick_value_score <= -10 then 'A'
        when avg_pick_value_score <= -5 then 'B+'
        when avg_pick_value_score <= 0 then 'B'
        when avg_pick_value_score <= 5 then 'C+'
        when avg_pick_value_score <= 10 then 'C'
        when avg_pick_value_score <= 15 then 'D'
        else 'F (Disaster)'
    end as draft_grade,

    -- Hit rate percentage
    round(100.0 * hits / nullif(total_picks, 0), 1) as hit_rate_pct,

    -- Rank managers by draft performance
    row_number() over (order by avg_pick_value_score) as draft_grade_rank

from manager_draft_summary
order by avg_pick_value_score
```

## Metrics Explained

### 1. Draft Slot

Formatted as "Round.Pick" (1.01, 2.05, etc.)

- Easy to read and understand
- Standard fantasy football notation

### 2. Pick Value Score

**Formula**: `Current Overall Rank - Draft Position`

**Examples**:

- Ja'Marr Chase: Drafted 1.01 (pick #1), currently Overall #20
  - Score: 20 - 1 = **+19** (bust, performing 19 spots worse)
- Puka Nacua: Drafted 8.03 (pick #47), currently Overall #15
  - Score: 15 - 47 = **-32** (steal! performing 32 spots better)

**Interpretation**:

- **Negative score** = Good! (Player outperforming draft slot)
- **Positive score** = Bad (Player underperforming draft slot)
- **Score near 0** = Fair (player performing as expected)

### 3. Pick Classification

- **Major Hit (Steal)**: Current rank 10+ spots better than draft
- **Hit**: Current rank better than draft slot
- **Fair**: Within ±10 spots of draft position
- **Miss**: Current rank 10-20 spots worse than draft
- **Major Miss (Bust)**: Current rank 20+ spots worse than draft

### 4. Draft Grade

Letter grade based on average pick value score:

- A+: Average pick value <= -15 (amazing)
- A: -10 to -15
- B: -5 to 0
- C: 0 to +10
- D/F: +10+  (disaster)

### 5. Round Performance

Track which rounds each manager hit/missed on:

- Round 1-3: High impact picks
- Rounds 4+: "Late round steals"

## Report Output

### Weekly Report Section

```markdown
## 📊 Draft Analysis - Week 6 Update

### League-Wide Draft Grades

| Rank | Manager | Grade | Best Pick | Worst Pick | Hit Rate |
|------|---------|-------|-----------|------------|----------|
| 1    | Sarah   | A     | Puka Nacua (8.03) - WR6 | Travis Kelce (2.12) - TE8 | 71% |
| 2    | Mike    | B+    | Breece Hall (1.04) - RB3 | DJ Moore (4.04) - WR45 | 62% |
| 3    | Ben     | C     | Tank Dell (7.01) - WR18 | Ja'Marr Chase (1.01) - WR10 | 50% |
| 4    | Jess    | C-    | Amon-Ra (2.08) - WR5 | Josh Allen (1.06) - QB8 | 43% |
| 5    | Tom     | D     | Kyren Williams (5.02) - RB12 | Jonathan Taylor (1.02) - RB28 | 33% |
| 6    | Alex    | F     | CeeDee Lamb (1.03) - WR22 | Mark Andrews (3.03) - TE15 | 28% |

### Biggest Steals (League-Wide)
1. **Puka Nacua** - Drafted 8.03, Currently WR6 (Overall #15) - *Sarah*
2. **Kyren Williams** - Drafted 5.02, Currently RB12 (Overall #25) - *Tom*
3. **Tank Dell** - Drafted 7.01, Currently WR18 (Overall #32) - *Ben*

### Biggest Busts (League-Wide)
1. **Jonathan Taylor** - Drafted 1.02, Currently RB28 (Overall #62) - *Tom*
2. **CeeDee Lamb** - Drafted 1.03, Currently WR22 (Overall #45) - *Alex*
3. **DJ Moore** - Drafted 4.04, Currently WR45 (Overall #78) - *Mike*

### Your Draft Report Card (Ben)

**Overall Grade: C** (Avg Pick Value: +3.2)

**Hits** (3):
- Tank Dell (7.01) - Drafted WR49, Currently WR18 ⭐ Steal!
- Stefon Diggs (3.01) - Drafted WR25, Currently WR19
- Raheem Mostert (6.06) - Drafted RB48, Currently RB32

**Fair** (4):
- Tyreek Hill (2.06) - Drafted WR12, Currently WR15
- Josh Jacobs (3.07) - Drafted RB18, Currently RB22
- (2 more players...)

**Misses** (3):
- Ja'Marr Chase (1.01) - Drafted WR1, Currently WR10
- Tony Pollard (4.06) - Drafted RB24, Currently RB38
- George Kittle (5.01) - Drafted TE6, Currently TE12

**Round-by-Round**:
- Round 1: C- (Chase underperforming)
- Round 2-3: B (Solid picks)
- Round 4-6: B+ (Mostert steal!)
- Round 7+: A (Tank Dell jackpot!)
```

## Dashboard Visualizations

### 1. Draft Heatmap

- **Rows**: Managers
- **Columns**: Draft picks (1-60)
- **Color**: Green (steal), Yellow (fair), Red (bust)
- **Hover**: Player name, draft slot, current rank

### 2. Draft Value Scatter Plot

- **X-axis**: Draft position
- **Y-axis**: Current overall rank
- **Diagonal line**: "Expected value" (draft pos = current rank)
- **Points above line**: Busts
- **Points below line**: Steals
- **Color by manager**

### 3. Draft Grade Bar Chart

- **X-axis**: Managers (sorted by grade)
- **Y-axis**: Average pick value score
- **Color**: Green (positive), Red (negative)

### 4. Round-by-Round Hit Rate

- **X-axis**: Rounds (1-10)
- **Y-axis**: Hit rate %
- **Shows**: Which rounds have most steals/busts

## Implementation Checklist

- [ ] Add Sleeper API endpoint for draft data
- [ ] Create `stg_draft_picks.sql` staging model
- [ ] Create `stg_player_rankings.sql` staging model
- [ ] Create `fct_draft_analysis.sql` mart model
- [ ] Create `fct_draft_grades.sql` mart model
- [ ] Add DBT tests for data quality
- [ ] Update `scripts/generate_report.py` with draft section
- [ ] Add draft visualizations to dashboard
- [ ] Test with real league draft data
- [ ] (Optional) Integrate FantasyPros API for expert rankings

## Future Enhancements

1. **Weekly Trend Tracking**: Show how draft grades change each week
2. **ADP Comparison**: Compare your league's draft to industry ADP
3. **Position-Specific Grades**: "Best QB drafter", "Best RB drafter"
4. **Trade Impact**: How trades affected your draft grade
5. **Multi-Year Analysis**: Track which managers draft well year-over-year
6. **Positional Scarcity**: Weight RB hits higher than WR hits

## Edge Cases & Questions

1. **What about players who haven't played?** (Injured all season)
   - **Proposed**: Rank them at bottom (999), classify as bust
2. **What about players dropped/traded?**
   - **Proposed**: Count for original drafter
3. **How to handle keeper/dynasty leagues?**
   - **Proposed**: Phase 2 feature
4. **FantasyPros API vs. Sleeper stats?**
   - **Proposed**: Start with Sleeper (simpler), add FantasyPros later

---

**Estimated Effort**: 5-6 hours
**Priority**: HIGH - Do after injury analysis
**Dependencies**: Sleeper draft API, player stats API
