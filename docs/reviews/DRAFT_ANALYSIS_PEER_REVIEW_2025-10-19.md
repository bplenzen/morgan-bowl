# Draft Analysis Peer Review - October 19, 2025

## Executive Summary

**Current Grade**: B+ (Methodologically sound, publishable with fixes)
**Target Grade**: A (Research-grade, publication-ready)
**Verdict**: Strong foundations; 5 critical fixes needed before publication

---

## 🎯 What's Excellent (Keep!)

- ✅ **Clear decomposition**: Luck vs. skill with separate schedule vs. matchup-timing components
- ✅ **Monte Carlo for expected wins**: Correctly avoids parametric distribution assumptions
- ✅ **FLEX replacement via simulation**: Right approach for mixed-FLEX formats
- ✅ **Process vs. outcome**: Draft-day opportunity cost separated from hindsight—methodologically honest
- ✅ **Zero-sum validations**: Great habit; keep those tests (add tolerances)

---

## 🚨 Critical Fixes (BLOCKING - Must Do First)

### 1. Fix Look-Ahead Bias in Draft Grading 🔴 **[BREAKING]**

**Issue**: Currently recalculating scarcity multipliers weekly using actual performance data, then using those to grade draft-day decisions. This is post-hoc information that wasn't available at draft time.

**Impact**: Draft grades are scientifically invalid without this fix.

**Fix**:

- Create draft-day parameter freeze system (YAML/JSON snapshot)
- Store at draft time: projections source + hash, replacement levels, scarcity multipliers, risk priors
- Lock all draft grading inputs to draft-day state only
- Separate "Draft Grade" (process-based, frozen params) from "Realized Value Report" (outcome-based, actual data)

**Implementation**:

- New file: `data/draft_day_parameters_2025.yml`
- New model: `int_draft_day_baseline.sql` (reads frozen params)
- Update: `fct_draft_analysis.sql` to use frozen baseline
- New model: `fct_draft_realized_value.sql` (in-season comparison, separate report)

**Tests**: Add test that verifies draft grades don't change when new weeks are ingested

**Effort**: 6-8 hours

---

### 2. Switch FLEX Simulation to Projection-Based (Not ADP) 🔴 **[BREAKING]**

**Issue**: Currently using ADP to allocate FLEX slots. ADP reflects market sentiment, not expected points.

**Impact**: Replacement levels for WR and RB are based on market psychology instead of expected scoring.

**Fix**:

- Allocate FLEX by projected PPG under league scoring settings
- Keep ADP-based version as comparative appendix ("What drafters actually did vs optimal allocation")

**Rationale**: Projections = expected points = what actually fills FLEX optimally

**Implementation**:

- Update `FLEX_REPLACEMENT_METHODOLOGY.md` with dual methodology
- Modify FLEX simulation to sort by projected_ppg (primary) and adp (secondary comparison)
- New fields: `flex_replacement_projection_based`, `flex_replacement_adp_based`
- Report both; use projection-based for VOR calculations

**Effort**: 3-4 hours

---

### 3. Multiplicative Risk Model with Position Priors 🟡 **[HIGH]**

**Issue**: Currently averaging volatility penalty + availability penalty. This can over/under-discount.

**Fix**:

```
Risk Factor = Availability Factor × Volatility Factor × Position Prior
Risk-Adjusted VOR = VOR × Risk Factor
```

**Implementation**:

- Availability Factor = games_played / games_expected (or snaps-based if available)
- Volatility Factor = f(CV) mapped to [0.7, 1.0] range
- Position Priors (fragility): RB = 0.85, WR = 0.95, TE = 0.90, QB = 1.00
- Optional: Bayesian priors (RB availability ~ Beta(8,2), update weekly)

**New model**: `int_player_risk_factors.sql` (replaces current averaging logic)

**Effort**: 4-5 hours

---

### 4. Pick-Value Curve for Opportunity Cost 🟡 **[HIGH]**

**Issue**: Current opportunity cost compares to "best available at position" but misses cross-position value and pick-slot expected value.

**Fix**:

- Fit smooth expected fantasy value by pick curve (LOESS regression)
- Use historical WAR/VOR vs pick number data
- `Decision Value = (Player Projection EV) - (Curve EV at pick)`
- Also report Positional Delta vs best alternative at ANY position

**Implementation**:

- New notebook: `analysis/pick_value_curve_calibration.ipynb`
- Fit curve using historical draft data (multi-year if available)
- Store curve parameters in draft-day freeze file
- New field in `fct_draft_analysis`: `decision_value` (pick EV - curve EV)

**Effort**: 5-6 hours

---

### 5. Add Uncertainty Quantification Everywhere 🟡 **[MEDIUM]**

**Issue**: Currently reporting point estimates without confidence intervals.

**Fix - Add**:

- Luck Analysis: 95% CI on expected wins from Monte Carlo distribution
- VOR: 80-95% CI via projection error bootstraps (sample from positional error residuals)
- Draft Grades: Show grade bands (e.g., "A: 89-93 ± CI") to avoid false precision
- Replacement Sensitivity: Re-run with ±1 FLEX slot (RB28 vs RB27/29) to show robustness

**Implementation**:

- New fields: `expected_wins_p05`, `expected_wins_p95`, `vor_lower_ci`, `vor_upper_ci`
- New visualization: Fan charts for luck analysis, bootstrap ribbons for VOR
- New test: `assert_sensitivity_analysis_stable.sql` (grades don't change dramatically with ±1 FLEX)

**Effort**: 4-5 hours

---

## 📈 Total Effort Estimate

**Critical Fixes**: 22-32 hours
**Payoff**: Transforms draft analysis from "interesting" to "publication-ready"

---

## 🎓 Methodology Enhancements (Should Do - Medium Priority)

6. **Calibrate Grades to Pick-Value Curve** - After building curve, re-calibrate A/B/C/D/F breakpoints to target distribution (3-4 hours)

7. **Weekly Replacement Level Variant** - Add weekly VOR variant for bye-week-aware analysis (6-8 hours) - Optional advanced feature

8. **Composite Luck Weight Validation** - Empirically validate 0.6/0.4 schedule/scoring weights via variance decomposition (2-3 hours)

9. **Enhanced Volatility Metrics** - Add % Top-12 weeks, % Sub-replacement weeks (already partially implemented!) (1 hour)

10. **Injury Treatment: Snaps-Based** - Use snaps-played share instead of games played (4-5 hours, requires data)

---

## 📋 Required Deliverables (Publication-Ready Artifacts)

### 1. Parameter Freeze System

**File**: `data/draft_day_parameters_2025.yml`

```yaml
draft_date: "2025-09-04"
projection_source: "FantasyPros_2025_PreseasonConsensus"
projection_hash: "sha256:abc123..."
replacement_levels:
  QB: {rank: 12, player: "Jordan Love", ppg: 15.8}
  RB: {rank: 28, player: "Najee Harris", ppg: 11.2}
  WR: {rank: 32, player: "Jordan Addison", ppg: 10.8}
  TE: {rank: 12, player: "Cole Kmet", ppg: 7.8}
scarcity_multipliers:
  QB: 1.00
  RB: 1.30
  WR: 1.05
  TE: 1.30
risk_priors:
  QB: {availability_mean: 0.95, volatility_floor: 0.90}
  RB: {availability_mean: 0.80, volatility_floor: 0.75}
  WR: {availability_mean: 0.88, volatility_floor: 0.80}
  TE: {availability_mean: 0.85, volatility_floor: 0.80}
```

### 2. FLEX Simulation Comparison Report

**Document**: `docs/FLEX_SIMULATION_COMPARISON.md`

- Table: FLEX composition by method (Projection-optimal vs ADP-driven)
- Chosen baseline with justification
- Sensitivity analysis

### 3. Pick Value Curve Notebook

**File**: `analysis/pick_value_curve_calibration.ipynb`

- Expected VOR by pick number (smooth LOESS curve)
- Residuals plot
- Curve parameters for opportunity cost

### 4. Uncertainty Visualization Suite

- Luck: Distribution of simulated wins per team (fan chart)
- VOR: Bootstrap confidence bands for top 30 players
- Draft Grades: Grade ranges with uncertainty ribbons

### 5. Ablation Study Report

**Analysis**: Recompute grades with:

- (a) No risk adjustment
- (b) No scarcity multipliers
- (c) RB24/WR24 baselines (no FLEX simulation)

**Output**: Delta table proving each component adds signal

---

## ✅ Acceptance Tests (Publication Readiness)

New test suite required:

1. `test_draft_parameters_frozen.sql` - Verify draft grades don't change when new weeks added
2. `test_flex_simulation_convergence.sql` - FLEX composition stable across projection sets
3. `test_flex_sanity_ppr.sql` - With PPR, WR ≥50% FLEX; TE ≤5% (non-premium)
4. `test_risk_factors_valid_range.sql` - All risk factors in [0.0, 1.0]
5. `test_luck_monte_carlo_convergence.sql` - Luck mean stabilizes by 5k trials
6. `test_zero_sum_with_tolerance.sql` - League-wide luck/skill sums to 0 ± 1e-6
7. `test_grade_distribution_sane.sql` - ~10-15% As, ~10-15% Ds/Fs, bell curve

---

## 🎯 Quick Wins (Do These First)

1. **Zero-Sum Validation with Tolerances** (30 min) - Update existing tests with explicit `|sum| < 1e-6`
2. **Enhanced Volatility Metrics** (1 hour) - Surface existing boom/bust rates in reports
3. **Explainability One-Liners** (2-3 hours) - Add `grade_explanation` field with natural language

---

## 🚀 Optional "Pro" Extensions (Future)

- **Bayesian hierarchical projections**: Shrink player projections toward positional means (early-season)
- **Team-level replacement**: Model waiver wire availability realistically (>50% WR3s rostered)
- **Causal framing**: Estimate manager WAR (wins added by start/sit decisions)

---

## 📊 Current vs Target State

| Dimension | Current Grade | Target Grade | Blocking Issues |
|-----------|---------------|--------------|-----------------|
| **Methodological Rigor** | A- | A | Look-ahead bias, FLEX leakage |
| **Statistical Treatment** | B+ | A | Missing CIs, no priors, no sensitivity |
| **Decision Analytics** | B+ | A | Needs pick-value curve anchoring |
| **Communication** | A- | A | Add explainability one-liners |

**Overall**: **B+** → **A** (publication-ready)

---

## 📚 Reference Materials to Create

1. **YAML spec**: Draft-day parameter freeze format
2. **Pseudocode**: Projection-driven FLEX simulation algorithm
3. **Methodology doc**: Pick-value curve fitting procedure
4. **Comparison table**: ADP-based vs Projection-based FLEX results
5. **Statistical appendix**: Bootstrap CI procedure for VOR

---

## 💬 Reviewer's Assessment

> "You've built two solid, research-grade frameworks. Lock pre-draft parameters, simulate FLEX from projections, quantify uncertainty everywhere, calibrate grades to a pick-value curve, and use multiplicative risk modeling. You're very close to a best-in-class internal whitepaper."

**Recommendation**: Complete the 5 critical fixes (#1-5) before sharing draft analysis publicly. After fixes, this would be publishable in Fantasy Football Analytics, The Athletic, or 4for4.

---

**Status**: 🔴 **BLOCKING** - Do not publish draft analysis until critical fixes are complete
**Priority**: **HIGHEST** - These fixes are prerequisite for v1.2.0 release
**Timeline**: 22-32 hours of focused work

---

**Last Updated**: October 19, 2025
**Reviewed By**: Expert Fantasy Football Analytics Peer Reviewer
**Next Steps**: See ROADMAP.md → Draft Analysis Methodology Improvements
