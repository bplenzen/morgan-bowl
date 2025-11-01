# Enhancement: Add Boris Chen Style Tier Visualizations

## Background

Boris Chen's tier-based visualizations (<http://www.borischen.co>) are the **gold standard** for fantasy draft analysis because they reduce cognitive load by grouping similar-value players into color-coded tiers.

**Current approach**: Raw VOR numbers (e.g., "adj_vor: 67.3")
**Better approach**: Visual tier boxes with colors

## Why This Matters

Users can quickly scan "Tier 1 (Elite)" vs "Tier 5 (Replacement)" without parsing numeric VOR values. This is especially helpful on mobile.

## Example Visualization

```
Tier 1 (Elite) - Green background
Tier 2 (High Value) - Blue background
Tier 3 (Solid) - Yellow background
Tier 4 (Depth) - Orange background
Tier 5 (Replacement) - Red background
```

## Implementation

### Step 1: Add tier calculation to fct_draft_performance.sql

Update `dbt/models/marts/fct_draft_performance.sql` to add a `vor_tier` column:

```sql
-- After line 649 (in draft_with_grades CTE, after value_verdict)

-- VOR TIER: Boris Chen style tiers for easy scanning
case
    when position in ('K', 'DEF') then NULL  -- No tiers for streaming
    when risk_adjusted_scarcity_vor >= 80 then 'TIER_1_ELITE'
    when risk_adjusted_scarcity_vor >= 60 then 'TIER_2_HIGH'
    when risk_adjusted_scarcity_vor >= 40 then 'TIER_3_SOLID'
    when risk_adjusted_scarcity_vor >= 20 then 'TIER_4_DEPTH'
    when risk_adjusted_scarcity_vor >= 0 then 'TIER_5_REPLACEMENT'
    else 'TIER_6_BUST'
end as vor_tier,

-- User-friendly tier label
case
    when position in ('K', 'DEF') then NULL
    when risk_adjusted_scarcity_vor >= 80 then 'Elite'
    when risk_adjusted_scarcity_vor >= 60 then 'High Value'
    when risk_adjusted_scarcity_vor >= 40 then 'Solid Starter'
    when risk_adjusted_scarcity_vor >= 20 then 'Depth/Flex'
    when risk_adjusted_scarcity_vor >= 0 then 'Replacement'
    else 'Bust'
end as vor_tier_label
```

### Step 2: Update dashboard to use color-coded tiers

In `analytics/dashboard.py`, add tier-based styling:

```python
# Add after POSITION_COLORS definition (around line 24)

VOR_TIER_COLORS = {
    "Elite": "#2ecc71",           # Green - top tier
    "High Value": "#3498db",       # Blue - strong value
    "Solid Starter": "#f39c12",    # Orange - solid
    "Depth/Flex": "#95a5a6",       # Gray - depth piece
    "Replacement": "#e74c3c",      # Red - replacement level
    "Bust": "#c0392b",             # Dark red - negative value
}

def get_tier_emoji(tier_label):
    """Add emoji for quick visual scan"""
    tier_emojis = {
        "Elite": "🌟",
        "High Value": "⭐",
        "Solid Starter": "✅",
        "Depth/Flex": "📊",
        "Replacement": "⚠️",
        "Bust": "❌",
    }
    return tier_emojis.get(tier_label, "")
```

### Step 3: Add tier column to draft board display

Update the draft board section (around line 875-926):

```python
# Add vor_tier_label to display columns
display_cols = [
    "draft_pick",
    "player_name",
    "position",
    "position_display",
    "manager_name",
    "vor_tier_label",  # NEW: Add tier
    "pick_grade",
    "value_verdict",
]

# Update column config
column_config = {
    "draft_pick": "Pick",
    "player_name": "Player",
    "position": None,
    "position_display": "Pos",
    "manager_name": "Manager",
    "vor_tier_label": st.column_config.TextColumn(
        "Tier",
        help="Boris Chen style value tier (Elite > High > Solid > Depth > Replacement)"
    ),
    "pick_grade": "Grade",
    "value_verdict": "Verdict",
}
```

### Step 4: Add tier-based color coding (optional enhancement)

For extra polish, add tier-based row styling:

```python
def style_draft_row(row):
    """Apply background color based on VOR tier"""
    tier = row.get("vor_tier_label", "")

    # K/DEF: Gray out
    if row.get("position", "") in ("K", "DEF"):
        return ["background-color: #f5f5f5; opacity: 0.6" for _ in row]

    # VOR tier colors
    bg_color = VOR_TIER_COLORS.get(tier, "white")
    return [f"background-color: {bg_color}; opacity: 0.3" for _ in row]

# Apply styling (replace style_position_row with style_draft_row)
styled_df = filtered_df[display_cols].style.apply(style_draft_row, axis=1)
```

### Step 5: Add tier distribution chart

Add a new visualization showing tier distribution:

```python
# After line 1213 (grade distribution chart)
st.subheader("Value Tier Distribution")

tier_counts = filtered_df["vor_tier_label"].value_counts()
tier_order = ["Elite", "High Value", "Solid Starter", "Depth/Flex", "Replacement", "Bust"]
tier_counts = tier_counts.reindex(tier_order, fill_value=0)

fig = px.bar(
    x=tier_counts.index,
    y=tier_counts.values,
    labels={"x": "Tier", "y": "Count"},
    title="Draft Picks by VOR Tier",
    color=tier_counts.index,
    color_discrete_map=VOR_TIER_COLORS,
)
st.plotly_chart(fig, use_container_width=True)
```

## Task

1. Read `dbt/models/marts/fct_draft_performance.sql`
2. Add `vor_tier` and `vor_tier_label` columns (after line 649)
3. Read `analytics/dashboard.py`
4. Add `VOR_TIER_COLORS` dictionary and helper functions
5. Update draft board to display tier column
6. Add tier distribution chart
7. Run DBT: `cd dbt && poetry run dbt build --select fct_draft_performance`
8. Test dashboard: `poetry run streamlit run analytics/dashboard.py`

## Completion Criteria

- [ ] VOR tiers are calculated in fct_draft_performance.sql
- [ ] Dashboard displays tier labels in draft board
- [ ] Tier distribution chart shows visual breakdown
- [ ] Tiers are color-coded for quick scanning
- [ ] All tests pass and dashboard runs without errors

## Validation

After implementing, check the Draft Analysis page:

1. Draft board should show "Tier" column with labels like "Elite", "High Value", etc.
2. Tiers should be color-coded (green for Elite, blue for High Value, etc.)
3. New tier distribution chart should appear below grade distribution

---

**Reference:**

- Boris Chen's approach: <http://www.borischen.co>
- BeerSheets (similar concept): <https://footballabsurdity.com/beersheet-files/>

---

**After completing this task:**

1. Mark #9 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 9` (or manually update)
3. Move to prompt #10
