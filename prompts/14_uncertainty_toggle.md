# Enhancement: Default Uncertainty Toggle to ON

## Problem

The "Show Advanced Stats (VOR, Uncertainty)" toggle in Draft Analysis defaults to **OFF** (`dashboard.py:840-842`):

```python
show_uncertainty = st.checkbox(
    "Show Advanced Stats (VOR, Uncertainty)", value=False  # ❌ Hidden by default
)
```

**Impact**: Most users never see your excellent uncertainty quantification work (VOR confidence intervals, grade uncertainty, etc.) because it's hidden behind an opt-in toggle.

## Why This Matters

You've done sophisticated uncertainty analysis (VOR lower/upper bounds, grade confidence intervals) that differentiates this platform from competitors. Hiding it by default means:

1. **Lost value**: Users don't see your best work
2. **Missed learning opportunity**: Users don't understand boom/bust risk
3. **Power users leave**: Advanced users want this data front-and-center

## Industry Standards

- **FantasyPros**: Shows confidence intervals in **tooltips** (always visible on hover)
- **ESPN**: Shows ± ranges in **small text** below main numbers
- **FiveThirtyEight**: All uncertainty metrics are **always visible** with good visual design

**No major platform hides uncertainty behind a toggle.**

## Solution Options

### Option A: Default Toggle to ON (Simplest)

```python
show_uncertainty = st.checkbox(
    "Show Advanced Stats (VOR, Uncertainty)", value=True  # ✅ Show by default
)
```

**Pros**: One-line fix
**Cons**: Still requires users to know toggle exists

### Option B: Remove Toggle, Always Show (Better)

Remove the toggle entirely and show uncertainty in a clean, non-overwhelming way:

```python
# Remove lines 840-842 entirely
# Update display_cols to ALWAYS include uncertainty (around line 885-892)

display_cols = [
    "draft_pick",
    "player_name",
    "position",
    "position_display",
    "manager_name",
    "adj_vor",           # Always show
    "vor_uncertainty",   # Always show
    "pick_grade",
    "grade_uncertainty", # Always show
    "value_verdict",
]
```

**Pros**: Users always see important data
**Cons**: Potentially overwhelming for casual users

### Option C: Show in Tooltips (Best UX)

Always show main metrics, put uncertainty in **help text tooltips**:

```python
# Remove the toggle
# Update column config to show uncertainty in tooltips:

column_config = {
    "draft_pick": "Pick",
    "player_name": "Player",
    "position": None,
    "position_display": "Pos",
    "manager_name": "Manager",
    "adj_vor": st.column_config.NumberColumn(
        "Adj VOR",
        format="%.1f",
        help="Value Over Replacement (risk-adjusted). Hover for confidence interval."
    ),
    "pick_grade": "Grade",
    "value_verdict": "Verdict",
}

# Add formatted VOR with ± in the dataframe itself
filtered_df["vor_display"] = filtered_df.apply(
    lambda row: (
        f"{row['adj_vor']:.1f} ± {row['vor_uncertainty']/2:.1f}"
        if pd.notna(row['vor_uncertainty']) and row['vor_uncertainty'] > 0
        else f"{row['adj_vor']:.1f}"
    ),
    axis=1
)

# Display vor_display instead of adj_vor
display_cols = [
    "draft_pick",
    "player_name",
    "position",
    "position_display",
    "manager_name",
    "vor_display",  # Shows "67.3 ± 8.2" format
    "pick_grade",
    "value_verdict",
]
```

## Recommended Implementation (Option C)

**Step 1**: Remove the toggle (lines 840-842)

**Step 2**: Create formatted columns with ± notation:

```python
# After line 871 (before applying styles), add formatted columns:

if 'vor_uncertainty' in filtered_df.columns and 'adj_vor' in filtered_df.columns:
    filtered_df["vor_display"] = filtered_df.apply(
        lambda row: (
            f"{row['adj_vor']:.1f} ± {row['vor_uncertainty']/2:.1f}"
            if pd.notna(row['vor_uncertainty']) and row['vor_uncertainty'] > 0
            else f"{row['adj_vor']:.1f}"
        ),
        axis=1
    )
else:
    filtered_df["vor_display"] = filtered_df["adj_vor"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "")

if 'grade_uncertainty' in filtered_df.columns and 'grade_score' in filtered_df.columns:
    filtered_df["grade_display"] = filtered_df.apply(
        lambda row: (
            f"{row['grade_score']:.0f} ± {row['grade_uncertainty']/2:.0f}"
            if pd.notna(row['grade_uncertainty']) and row['grade_uncertainty'] > 0
            else f"{row['grade_score']:.0f}"
        ),
        axis=1
    )
else:
    filtered_df["grade_display"] = filtered_df["grade_score"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "")
```

**Step 3**: Update display columns (around line 875):

```python
display_cols = [
    "draft_pick",
    "player_name",
    "position",
    "position_display",
    "manager_name",
    "vor_display",    # NEW: Shows "67.3 ± 8.2"
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
    "vor_display": st.column_config.TextColumn(
        "VOR ± CI",
        help="Value Over Replacement with 95% confidence interval (wider = more volatile)"
    ),
    "pick_grade": "Grade",
    "value_verdict": "Verdict",
}
```

**Step 4**: Update Best/Worst picks sections to use new columns (around line 929-984)

**Step 5**: Remove conditional logic for `show_uncertainty` (all references to this variable)

## Task

1. Read `analytics/dashboard.py`
2. Decide which option you prefer (I recommend **Option C** for best UX)
3. Remove the uncertainty toggle checkbox (lines 840-842)
4. Add formatted columns with ± notation
5. Update all display_cols and column_config to use formatted columns
6. Test dashboard: `poetry run streamlit run analytics/dashboard.py`
7. Verify uncertainty is visible but not overwhelming

## Completion Criteria

- [ ] Uncertainty toggle is removed (or defaulted to ON if keeping toggle)
- [ ] VOR and grade uncertainty are visible (either in columns or tooltips)
- [ ] Display is clean and not overwhelming
- [ ] Dashboard runs without errors

## Validation

After implementing:

1. Navigate to Draft Analysis tab
2. Draft board should show uncertainty (either inline or on hover)
3. Best/Worst picks should show uncertainty
4. Confidence interval chart should always be visible (if sample size sufficient)

---

**Design Philosophy:**

- **Default to transparency**: Show uncertainty, don't hide it
- **Progressive disclosure**: Simple view by default, details on hover/expand
- **Trust users**: Power users appreciate seeing confidence intervals

---

**After completing this task:**

1. Mark #14 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 14` (or manually update)
3. Move to prompt #15
