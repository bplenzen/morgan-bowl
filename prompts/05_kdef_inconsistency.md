# Fix Warning: K/DEF Handling Inconsistency

## Problem

Kickers (K) and Defenses (DEF) are correctly excluded from VOR-based draft grading in the backend, but they still appear in the dashboard's draft analysis without any explanation to users.

**Backend (Correct):**

- `fct_draft_performance.sql:313-314` correctly sets `pick_grade = NULL` for K/DEF
- `fct_draft_performance.sql:460` correctly sets `grade_score = NULL` for K/DEF

**Frontend (Confusing):**

- `dashboard.py:850-871` still displays K/DEF in draft board
- No explanation why they don't have grades
- Position display shows "K" or "DEF(NR)" (not ranked) but no tooltip

## Impact

Users see K/DEF picks in draft board with blank/NULL grades and no explanation. This looks like a bug rather than intentional design.

## Required Fix

Add user-facing explanation for why K/DEF aren't graded, and optionally filter them from draft analysis views.

## Solution Options

### Option A: Add Tooltips (Quick Fix)

In `dashboard.py`, add a helper text when displaying K/DEF:

```python
# Around line 858-867 in format_position_with_rank function
if position in ("K", "DEF"):
    return position  # No ranking for streaming positions
```

Update column config to add help text:

```python
# Around line 900
column_config = {
    "position_display": st.column_config.TextColumn(
        "Pos",
        help="K/DEF are streaming positions and not graded for draft value"
    ),
    # ...
}
```

### Option B: Filter K/DEF Entirely (Cleaner)

Add a filter toggle in the dashboard:

```python
# After line 803 (manager filter)
include_streaming = st.checkbox(
    "Show K/DEF picks",
    value=False,
    help="Kickers and defenses are streaming positions not evaluated for draft value"
)

filtered_df = (
    draft_df
    if selected_manager == "All"
    else draft_df[draft_df["manager_name"] == selected_manager]
)

# NEW: Filter out K/DEF unless explicitly requested
if not include_streaming:
    filtered_df = filtered_df[~filtered_df["position"].isin(["K", "DEF"])]
```

### Option C: Show K/DEF with Special Styling (Best UX)

Keep them visible but gray them out:

```python
def style_position_row(row):
    """Apply background color to entire row based on position"""
    position = row.get("position", "")

    # K/DEF: Gray out (streaming positions)
    if position in ("K", "DEF"):
        return ["background-color: #f5f5f5; opacity: 0.6" for _ in row]

    # Regular positions: color by position
    bg_color = POSITION_COLORS.get(position, "white")
    return [f"background-color: {bg_color}" for _ in row]
```

And update grade display:

```python
# In filtered_df creation around line 850
filtered_df["pick_grade"] = filtered_df.apply(
    lambda row: "N/A (Streaming)" if row["position"] in ["K", "DEF"] else row["pick_grade"],
    axis=1
)
```

## Task

1. Read `analytics/dashboard.py`
2. Choose which option you prefer (I recommend **Option C** for best UX)
3. Implement the changes
4. Test the dashboard: `poetry run streamlit run analytics/dashboard.py`
5. Navigate to Draft Analysis tab and verify K/DEF display correctly

## Completion Criteria

- [ ] K/DEF picks are clearly distinguished from regular positions
- [ ] Users understand why K/DEF don't have letter grades
- [ ] No confusion about "missing" grades
- [ ] Dashboard runs without errors

## Validation

After fixing, check the Draft Analysis page:

1. K/DEF picks should be visually distinct (grayed out or filtered)
2. Hovering over K/DEF should show tooltip explaining they're streaming positions
3. Grade columns for K/DEF should show "N/A" or similar

---

**Industry Standard Reference:**

- FantasyPros: Completely hides K/DEF from draft grades
- Sleeper: Shows K/DEF but grays them out with "N/A" grades
- ESPN: Shows K/DEF with asterisk: "*Streaming position - not graded"

---

**After completing this task:**

1. Mark #5 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 5` (or manually update)
3. Move to prompt #6
