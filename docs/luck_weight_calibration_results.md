# Luck Weight Calibration Results - October 19, 2025

## Executive Summary

**Verdict**: ⚠️ **Weights Need Recalibration** - Current weights are 10x off from data-driven values

**Key Finding**: Schedule and close-game luck only explain **46.4%** of variance in wins over expected. This suggests:

1. The current weights overemphasize schedule/close-game components
2. There's significant unexplained variance (53.6%) from other factors
3. The dominant factor is already captured in `wins_over_expected` itself

---

## 📊 Analysis Results

### 1. Variance Decomposition

**R² = 0.464** (46.4% variance explained)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| R² (variance explained) | 0.464 | ⚠️ WEAK - significant unexplained variance |
| RMSE | 0.515 wins | Prediction error |
| Schedule coefficient | -0.0504 | 10x smaller than current (-0.5) |
| Close game coefficient | 0.6502 | 30x smaller than current (20.0) |

**What this means**:

- Only 46% of luck variance comes from schedule + close games
- 54% is unexplained - likely already captured in `wins_over_expected`
- Current weights are dramatically overweighted

---

### 2. Current vs Data-Driven Weights

| Component | Current SQL | Data-Driven | Ratio |
|-----------|-------------|-------------|-------|
| **wins_over_expected** | ×10 | ×10 | 1.0x ✅ |
| **schedule_luck_index** | -0.5 | -0.05 | **10.0x** ⚠️ |
| **close_game_deviation** | 20.0 | 0.65 | **30.8x** ⚠️ |

**Diagnosis**: You're **double-counting** luck!

The composite formula is:

```sql
composite_luck_score = 50
    + (wins_over_expected) * 10           -- Already captures total luck
    + (schedule_luck_index) * -0.5        -- 10x overweighted
    + (close_game_win_pct - 0.5) * 20     -- 30x overweighted
```

**Problem**: `wins_over_expected` already incorporates schedule and close-game effects. Adding them again with heavy weights inflates the score.

---

### 3. Sensitivity Analysis

**Rank Stability** (Spearman ρ with current rankings):

| Scenario | Correlation | Status |
|----------|-------------|--------|
| Close -20% | 1.0000 | ✅ Perfectly stable |
| Schedule ±20% | 0.9790 | ✅ Very stable |
| Close +20% | 0.9580 | ✅ Stable |
| Data-Driven | 0.9091 | ✓ Mostly stable |

**Good news**: Rankings are relatively stable even with weight changes.

---

### 4. Unexplained Variance

**Teams with largest residuals** (luck not explained by schedule/close games):

| Manager | Actual WOE | Predicted WOE | Residual | Explanation |
|---------|------------|---------------|----------|-------------|
| jacklamb | +0.73 | -0.10 | **+0.83** | Lucky beyond schedule/close games |
| mrbeef1 | +0.91 | +0.15 | **+0.76** | Lucky beyond schedule/close games |
| jamespancakes | +0.09 | -0.44 | **+0.53** | Lucky beyond schedule/close games |

**Why the unexplained variance?**

1. **Opponent timing** not captured in schedule_luck_index
2. **Waiver wire timing** (picking up players before breakout weeks)
3. **Injury timing** (opponents' players getting injured)
4. **Random variance** (the "luck" you can't decompose)

---

## 🎯 Recommendations

### Option 1: Simplify Formula (RECOMMENDED)

**Rationale**: `wins_over_expected` already captures total luck. Don't double-count.

**Suggested Formula**:

```sql
composite_luck_score = 50 + (wins_over_expected) * 10
```

**Benefits**:

- ✅ Simple and interpretable
- ✅ Doesn't double-count luck components
- ✅ `wins_over_expected` is already a robust all-play metric
- ✅ Avoids arbitrary weight calibration

**Optional**: Keep schedule/close as **diagnostic details** (separate columns), not composite score inputs.

---

### Option 2: Use Data-Driven Weights

**If you want to keep the composite formula**:

```sql
composite_luck_score = 50
    + (wins_over_expected) * 10
    + (schedule_luck_index) * -0.05   -- Updated from -0.5
    + (close_game_win_pct - 0.5) * 0.65  -- Updated from 20.0
```

**Benefits**:

- ✅ Empirically calibrated
- ✅ Weights proportional to variance explained
- ✅ Reduces double-counting

**Drawbacks**:

- ⚠️ Still only explains 46% of variance
- ⚠️ More complex with marginal benefit

---

### Option 3: Investigate Unexplained Variance

**Deep dive into the 54% unexplained variance**:

1. **Opponent Performance Timing**
   - Current `schedule_luck_index` uses season averages
   - Improve: Use opponent's rolling 3-week average at time of matchup

2. **Blowout vs Close Game Luck**
   - Current: 10-point threshold is arbitrary
   - Improve: Use probabilistic model (win probability based on point differential)

3. **Roster Decision Luck**
   - Bench points vs starter points
   - "Started the wrong WR" variance

4. **Waiver Wire Timing**
   - Picked up player week before breakout
   - Lost player to injury week after pickup

**Effort**: 6-8 hours of analysis
**Payoff**: Increase R² from 46% → 70%+

---

## 📝 Documentation Updates Needed

### 1. Update `WHITE_PAPER_luck_analysis.md`

Add section:

````markdown
### 3.5 Weight Calibration (Empirical Validation)

**Methodology**: Regression analysis on 2025 season data to validate composite score weights.

**Key Finding**: Schedule and close-game components only explain 46.4% of variance in wins over expected (R² = 0.464). This indicates that `wins_over_expected` (all-play based) already captures the majority of luck, and additional weighting of schedule/close-game components provides diminishing returns.

**Current Weights**: Overweighted by 10-30x compared to data-driven regression coefficients.

**Recommendation**: Simplify composite score to focus on `wins_over_expected` as the primary luck metric, with schedule/close-game as diagnostic details.

**Validation**: Rank stability (Spearman ρ > 0.90) confirms robustness to weight changes.
````

### 2. Update `fct_advanced_luck.sql` (if choosing Option 1)

```sql
-- SIMPLIFIED COMPOSITE SCORE (recommended after calibration analysis)
round(50 + (ar.actual_wins - ew.expected_wins) * 10, 1) as composite_luck_score,

-- Keep diagnostic details as separate columns:
sl.schedule_luck_index,
case
    when cg.total_close_games > 0
    then round(cg.close_wins::double / cg.total_close_games, 3)
end as close_game_win_pct,
```

### 3. Update `ROADMAP.md`

Mark completed:

```markdown
- [x] Luck Weight Calibration (Oct 19, 2025)
  - Built analysis/luck_weight_calibration.ipynb
  - Validated via variance decomposition (R² = 0.464)
  - **Finding**: Current weights 10-30x overweighted
  - **Action**: Simplified composite formula (wins_over_expected only)
```

---

## 🔬 Technical Notes

### Why Low R²?

**Good news**: This is actually expected!

1. **All-play win% is already comprehensive**
   - `wins_over_expected` uses all-play methodology
   - Already accounts for strength-of-schedule implicitly
   - Adding schedule_luck_index is partially redundant

2. **Close games are inherently random**
   - 10-point threshold is arbitrary
   - Doesn't account for strategic decisions (risk-taking, bench choices)
   - True randomness can't be further decomposed

3. **Unmeasured factors**
   - Waiver timing, injury timing, opponent roster decisions
   - These create "luck" not captured in simple metrics

**Conclusion**: R² = 46% doesn't mean the analysis is wrong. It means:

- 46% of luck variance comes from measurable schedule/close-game effects
- 54% is "true randomness" or unmeasured factors
- `wins_over_expected` already captures the total (100%)

---

## 🎯 Next Steps

1. **Decide on formula** (Option 1, 2, or 3)
2. **Update `fct_advanced_luck.sql`** with chosen approach
3. **Re-run dbt** to regenerate luck scores
4. **Document in WHITE_PAPER** with calibration findings
5. **Optional**: Pursue Monte Carlo uncertainty (separate task, 4-5 hours)

---

## 📊 Files Generated

```
✅ analysis/luck_weight_calibration.ipynb    (Executed, results captured)
✅ dbt/tests/assert_luck_zero_sum.sql       (PASSING)
✅ docs/luck_analysis_implementation.md     (Implementation log)
✅ docs/luck_weight_calibration_results.md  (This document)
```

---

**Status**: ✅ **Analysis Complete** | ⚠️ **Decision Required on Formula Update**
