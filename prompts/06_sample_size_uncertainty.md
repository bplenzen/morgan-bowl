# Fix Warning: Insufficient Sample Size for Uncertainty Metrics

## Problem

The dashboard shows confidence intervals and uncertainty metrics after only 2 games (`dashboard.py:1067`):

```python
st.info(
    "📊 Uncertainty data will appear after Week 2 (need 2+ games for variance calculations)"
)
```

**This is statistically irresponsible.** With n=2, the standard deviation calculation has only 1 degree of freedom (divide by n-1), making variance estimates extremely unreliable.

## Impact

Users see ±30-40 point uncertainty ranges that are artifacts of small sample sizes, not real player volatility. This misleads decision-making.

Example: Player with 2 games scoring [25, 15]:

- Mean: 20 PPG
- Stddev: 7.07 (seems reasonable)
- But with n=2, this stddev has 70% confidence interval of [3.5, 30] - it's essentially meaningless!

## Industry Standards

- **ESPN**: Doesn't show "consistency ratings" until Week 6
- **FantasyPros**: Requires 4+ games for "boom/bust" classifications
- **Statistical best practice**: Minimum n=5 for variance estimates, n=10 for reliable CI

## Required Fix

Increase minimum games threshold from 2 to **5 games** before showing uncertainty metrics.

## Solution

Update `analytics/dashboard.py` in multiple places:

### 1. Dynamic Threshold Calculation (Line 991-995)

```python
# Current (TOO LOW):
MIN_AVAILABILITY_PCT = 0.60
min_games_threshold = max(3, int(weeks_completed * MIN_AVAILABILITY_PCT))

# Fixed:
MIN_AVAILABILITY_PCT = 0.60
min_games_threshold = max(5, int(weeks_completed * MIN_AVAILABILITY_PCT))
# Always require at least 5 games, even if only 6 weeks have been played
```

### 2. Info Message (Line 1066-1068)

```python
# Current:
st.info(
    "📊 Uncertainty data will appear after Week 2 (need 2+ games for variance calculations)"
)

# Fixed:
st.info(
    "📊 Uncertainty data will appear after Week 5 (need 5+ games for reliable variance estimates)"
)
```

### 3. Update Uncertainty Filter (Line 1008-1011)

Already correctly filters based on min_games_threshold, but update the explanation text (line 997-1004):

```python
st.markdown(
    f"""
**Understanding Uncertainty:**
- **Wide confidence intervals** = High volatility, boom-or-bust player
- **Narrow confidence intervals** = Consistent, reliable floor
- Uncertainty decreases as season progresses (more data)
- *Showing players with ≥{min_games_threshold} games for reliable estimates (minimum {int(MIN_AVAILABILITY_PCT*100)}% availability through Week {weeks_completed})*
"""
)
```

## Task

1. Read `analytics/dashboard.py`
2. Update minimum threshold from `max(3, ...)` to `max(5, ...)`
3. Update info message from "Week 2 (need 2+ games)" to "Week 5 (need 5+ games)"
4. Update explanation text to clarify reliability requirement
5. Test the dashboard: `poetry run streamlit run analytics/dashboard.py`
6. Navigate to Draft Analysis → Confidence Interval Analysis section
7. Verify uncertainty metrics only show for players with 5+ games

## Completion Criteria

- [ ] Minimum games threshold is 5 (not 2 or 3)
- [ ] Info message correctly states "Week 5" requirement
- [ ] Uncertainty visualizations only show players with sufficient sample size
- [ ] Dashboard runs without errors

## Validation

After Week 8, with min_games_threshold=5:

1. Players with 4 games: NOT shown in uncertainty analysis
2. Players with 5+ games: Shown with confidence intervals
3. Info text should say "≥5 games (60% availability through Week 8)"

---

**Statistical Justification:**
With n=5 games:

- Stddev has 4 degrees of freedom (reasonable estimate)
- 95% CI for variance: ~40% of true value (acceptable)
- Coefficient of variation estimates are meaningful

With n=2 games:

- Stddev has 1 degree of freedom (extremely noisy)
- 95% CI for variance: ~14x the true value (useless)
- Essentially just showing "these two games were different"

---

**After completing this task:**

1. Mark #6 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 6` (or manually update)
3. Move to prompt #7
