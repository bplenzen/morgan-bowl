# Fix Warning: No Trade Tracking in Draft Grades

## Problem

Draft grades in `fct_draft_performance.sql` are attributed to the **original drafter**, but if a player was traded to another team, the grade still shows on the original drafter's record.

For example:

- Team A drafts Saquon Barkley (Round 1, Pick 5)
- Barkley has an A+ season
- Team A trades Barkley to Team B in Week 4
- **Current behavior**: Team A still gets credit for the A+ draft pick, even though they traded him away
- **Expected behavior**: Either show trade status or split "Draft Decision" vs "Current Value"

## Impact

In leagues with active trading, draft grades become misleading mid-season. Teams that traded away good picks get undeserved credit; teams that traded for good players don't get credit.

## Industry Standards

- **FantasyPros Draft Analyzer**: Shows "Drafted by Team A → Traded to Team B (Week 3)"
- **Sleeper**: Adds a "Traded" badge to draft recap
- **ESPN**: Shows asterisk with trade details in draft report card

## Required Fix (Phase 1: Basic Trade Tracking)

Add trade metadata to draft performance table so users can see which picks were traded.

### Implementation

#### Step 1: Add trade flag to fct_draft_performance.sql

Update `fct_draft_performance.sql` to include trade information:

```sql
-- After line 655 (before final select)
with_trade_info as (
    select
        dwg.*,
        r.owner_id,
        u.display_name as manager_name,

        -- Check if player was traded (current roster different from draft roster)
        case
            when r.owner_id != dwg.roster_id then true
            else false
        end as was_traded,

        -- Get current owner if traded
        case
            when r.owner_id != dwg.roster_id then
                (select display_name from {{ ref('stg_users') }} where user_id = r.owner_id)
            else null
        end as current_owner_name

    from draft_with_grades as dwg
    left join rosters as r
        on dwg.player_id = ANY(r.players)  -- Current roster
    left join users as u
        on dwg.roster_id = u.user_id  -- Original drafter
)

select * from with_trade_info
order by pick_no
```

However, there's a problem: the current data model doesn't track transactions properly. You have `stg_transactions` but it's not being used.

#### Step 2: Check if transaction data is available

First, verify if you have transaction data:

```sql
-- Check transactions table
SELECT transaction_type, COUNT(*)
FROM main_analytics.stg_transactions
GROUP BY transaction_type;
```

If you see `trade` transactions, proceed with Step 3. If not, note this as a limitation.

#### Step 3: Add trade tracking (if transaction data exists)

If transactions are available, create a helper model:

**Create `dbt/models/intermediate/int_player_trade_history.sql`:**

```sql
{{ config(materialized='table') }}

-- Track when players were traded and to whom

with transactions as (
    select * from {{ ref('stg_transactions') }}
    where transaction_type = 'trade'
),

draft_picks as (
    select player_id, roster_id as original_roster_id
    from {{ ref('stg_draft_picks') }}
),

rosters as (
    select * from {{ ref('stg_rosters') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

trade_summary as (
    select
        dp.player_id,
        dp.original_roster_id,
        t.roster_id as current_roster_id,
        t.created_at as trade_date,
        row_number() over (partition by dp.player_id order by t.created_at desc) as trade_rank
    from draft_picks dp
    left join transactions t
        on dp.player_id = ANY(t.adds)  -- Player was added via trade
    where t.transaction_type = 'trade'
)

select
    player_id,
    original_roster_id,
    current_roster_id,
    trade_date,
    (select display_name from users where user_id =
        (select owner_id from rosters where roster_id = original_roster_id)
    ) as original_owner_name,
    (select display_name from users where user_id =
        (select owner_id from rosters where roster_id = current_roster_id)
    ) as current_owner_name,
    trade_rank = 1 as is_most_recent_trade
from trade_summary
```

#### Step 4: Update dashboard to show trade status

In `analytics/dashboard.py`, add a trade indicator column:

```python
# Around line 880, add to display columns:
if 'was_traded' in filtered_df.columns:
    filtered_df['ownership'] = filtered_df.apply(
        lambda row: f"→ {row['current_owner_name']}" if row['was_traded'] else "",
        axis=1
    )
    display_cols.insert(5, 'ownership')  # After manager_name
```

## Task (Simplified - Detection Only)

Since full trade tracking requires transaction data analysis, let's start simpler:

1. Check if you have trade transaction data available
2. If yes, proceed with full implementation above
3. If no, add a note to draft analysis explaining limitation

### Quick Implementation (No Transaction Data)

Just add a disclaimer to the dashboard:

```python
# In dashboard.py, Draft Analysis section (after line 695)
st.info("""
**Note on Draft Grades:**
Grades reflect the quality of the original draft decision by the drafter.
If a player was traded, the grade still applies to the team that drafted them.
(Trade tracking coming soon!)
""")
```

## Completion Criteria

- [ ] Trade tracking limitation is documented (either in dashboard or model)
- [ ] If transaction data exists, trade flags are added to draft performance
- [ ] Dashboard clearly shows which picks were traded (if tracking is implemented)
- [ ] Users understand grades reflect original draft decisions

## Future Enhancement

Full trade tracking would require:

1. Parsing transaction data to identify trades
2. Tracking trade dates and counter-parties
3. Splitting "Draft Grade" (original decision) from "Current Value" (current owner)

This is a larger project - for now, just document the limitation.

---

**After completing this task:**

1. Mark #8 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 8` (or manually update)
3. Move to prompt #9
