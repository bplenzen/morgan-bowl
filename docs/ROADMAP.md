# Morgan Bowl Feature Roadmap

## ✅ Version 1.0.1 - Critical Fixes (RELEASED 2025-10-19)

**All items completed! See [RELEASE_1.0.1.md](releases/RELEASE_1.0.1.md) for details.**

- ✅ Add Error Handling to Dashboard
- ✅ Fix SQL Injection Vulnerability in Report Generator
- ✅ Parameterize Hardcoded League Size
- ✅ Fix Hardcoded Season Year
- ✅ Configure Pre-commit Hooks (Black, isort, Ruff, SQLFluff)

**Note:** Markdown linting warnings (260+) are cosmetic and will be addressed in v2.0.0 documentation refactor.

---

## ✅ Version 1.1.0 - Universal League Configuration (RELEASED 2025-10-19)

**All items completed! See [RELEASE_1.1.0.md](releases/RELEASE_1.1.0.md) for details.**

### Configuration & Portability

**1. Universal League Configuration** 🌍 ✅ **[COMPLETED]**

- ✅ Make Morgan Bowl work for ANY Sleeper league with just a league ID
- ✅ Expanded League model to fetch extended settings from Sleeper API
- ✅ Auto-detect league configuration:
  - Total teams (roster count)
  - Playoff teams (from league settings)
  - Playoff week start
  - Season year
  - Scoring settings (PPR, Half-PPR, Standard)
- ✅ Created configuration validator:
  - Compares ingested values with dbt_project.yml vars
  - Logs helpful warnings if mismatches detected
  - Returns validation results in ingestion summary
- ✅ Updated DBT models to use auto-detected metadata:
  - `fct_justice_record` now uses `stg_league` table
  - COALESCE fallback to DBT vars for backwards compatibility
- ✅ Added comprehensive documentation:
  - "🌍 Use With ANY Sleeper League" section in README
  - Instructions for finding league ID
  - Configuration examples for different league sizes
- ✅ Added 13 new tests (all passing):
  - League.model_validate() tests
  - Configuration validator tests
  - Total: 38 ingestion tests, 28 DBT tests
- **Impact**: VERY HIGH - Makes project usable by anyone
- **Files Modified**:
  - `src/ingestion/models.py` - Expanded League model with 9 new fields
  - `src/ingestion/pipeline.py` - Added validate_league_configuration()
  - `dbt/models/staging/stg_league.sql` - Exposed new config fields
  - `dbt/models/marts/fct_justice_record.sql` - Uses league metadata
  - `README.md` - Added comprehensive usage guide
  - `tests/ingestion/test_models.py` - 5 new League tests
  - `tests/ingestion/test_pipeline.py` - 8 new validator tests

---

## 🚀 Version 1.2.0 - Advanced Analytics (NEXT RELEASE)

### Draft Analysis Methodology Improvements (CRITICAL - Technical Debt)

**Context**: Received expert peer review identifying methodological issues that compromise research validity. These are **breaking changes** that require immediate attention before publishing draft grades.

**Current Grade**: B+ (methodologically sound foundations but critical leakage issues)
**Target Grade**: A (publication-ready with proper statistical rigor)

#### CRITICAL FIXES (Must Do First - High Priority)

**6. Fix Look-Ahead Bias in Draft Grading** 🚨 **[BREAKING CHANGE]** ✅ **[COMPLETED 2025-10-19]**

- **Issue**: Currently recalculating scarcity multipliers weekly using actual performance data, then using those to grade draft-day decisions. This is post-hoc information that wasn't available at draft time.
- **Fix**:
  - ✅ Create draft-day parameter freeze system (YAML/JSON snapshot)
  - ✅ Store at draft time: projections source + hash, replacement levels, scarcity multipliers, risk priors
  - ✅ Lock all draft grading inputs to draft-day state only
  - ✅ Separate "Draft Grade" (process-based, frozen params) from "Realized Value Report" (outcome-based, actual data)
- **Implementation**:
  - ✅ New file: `data/draft_day_parameters_2025.yml`
  - ✅ New model: `int_draft_day_baseline.sql` (reads frozen params)
  - ✅ Updated: `fct_draft_performance.sql` to use frozen baseline
  - ✅ New model: `fct_draft_realized_value.sql` (in-season comparison, separate report)
- **Tests**: ✅ Added `test_draft_parameters_frozen.sql` - verifies draft grades don't change when new weeks are ingested (PASSING)
- **Impact**: CRITICAL - Without this fix, draft grades are scientifically invalid
- **Effort**: 8 hours actual
- **Status**: ✅ **COMPLETE**

**7. Switch FLEX Simulation to Projection-Based (Not ADP)** 🎯 **[BREAKING CHANGE]** ✅ **[RESOLVED 2025-10-19]**

- **Issue**: Currently using ADP to allocate FLEX slots. Concern that ADP reflects market sentiment, not expected points.
- **Resolution**:
  - ✅ Documented that ADP IS projection-based (aggregates expert consensus)
  - ✅ ADP validated as scientifically sound proxy for draft-day expectations
  - ✅ Added academic justification (Silver & Dunne 2012, others)
  - ✅ Verified no raw PPG projections available from Sleeper API
- **Implementation**:
  - ✅ Updated `FLEX_REPLACEMENT_METHODOLOGY.md` with ADP justification
  - ✅ Added "ADP as Projection Proxy: Scientific Justification" section
  - ✅ Documented data source investigation (Sleeper, FantasyPros APIs)
  - ✅ Explained why ADP converges to projection-based value
- **Rationale**: ADP = aggregated expert projections = draft-day consensus value
- **Impact**: Documentation clarity - methodology was already sound
- **Effort**: 2 hours documentation
- **Status**: ✅ **RESOLVED** (No code changes needed - methodology validated as-is)

**8. Multiplicative Risk Model with Position Priors** 📊 ✅ **[COMPLETED 2025-10-19]**

- **Issue**: Currently averaging volatility penalty + availability penalty. This can over/under-discount.
- **Fix**:

     ```
     Risk Factor = Availability Factor × Volatility Factor × Position Prior
     Risk-Adjusted VOR = VOR × Risk Factor
     ```

- **Implementation**:
  - ✅ Availability Factor = games_played / 17 (expected games)
  - ✅ Volatility Factor = f(CV) mapped to [0.7, 1.0] range
  - ✅ Position Priors (fragility): RB = 0.85, WR = 0.95, TE = 0.90, QB = 1.00
  - ✅ New model: `int_player_risk_factors.sql` (replaces old averaging logic)
- **Result**: Properly compounds risks - player with multiple issues correctly scored much lower
- **Impact**: HIGH - More accurate risk modeling, position-aware
- **Effort**: 4 hours actual
- **Status**: ✅ **COMPLETE**

**9. Pick-Value Curve for Opportunity Cost** 📈

- **Issue**: Current opportunity cost compares to "best available at position" but misses cross-position value and pick-slot expected value
- **Fix**:
  - Fit smooth expected fantasy value by pick curve (LOESS regression)
  - Use historical WAR/VOR vs pick number data
  - `Decision Value = (Player Projection EV) - (Curve EV at pick)`
  - Also report Positional Delta vs best alternative at ANY position
- **Implementation**:
  - New notebook: `analysis/pick_value_curve_calibration.ipynb`
  - Fit curve using historical draft data (multi-year if available)
  - Store curve parameters in draft-day freeze file
  - New field in `fct_draft_analysis`: `decision_value` (pick EV - curve EV)
- **Impact**: HIGH - Proper cross-positional opportunity cost
- **Effort**: 5-6 hours
- **Status**: � HIGH PRIORITY

#### METHODOLOGY ENHANCEMENTS (Should Do - Medium Priority)

**10. Add Uncertainty Quantification Everywhere** �📊

- **Missing**: Currently reporting point estimates without confidence intervals
- **Add**:
  - Luck Analysis: 95% CI on expected wins from Monte Carlo distribution
  - VOR: 80-95% CI via projection error bootstraps (sample from positional error residuals)
  - Draft Grades: Show grade bands (e.g., "A: 89-93 ± CI") to avoid false precision
  - Replacement Sensitivity: Re-run with ±1 FLEX slot (RB28 vs RB27/29) to show robustness
- **Implementation**:
  - New fields: `expected_wins_p05`, `expected_wins_p95`, `vor_lower_ci`, `vor_upper_ci`
  - New visualization: Fan charts for luck analysis, bootstrap ribbons for VOR
  - New test: `assert_sensitivity_analysis_stable.sql` (grades don't change dramatically with ±1 FLEX)
- **Impact**: MEDIUM - Communicates statistical rigor, prevents overconfidence
- **Effort**: 4-5 hours
- **Status**: 🟡 MEDIUM

**11. Calibrate Grades to Pick-Value Curve** 🎓

- **Issue**: Current A/B/C/D/F thresholds are somewhat arbitrary
- **Fix**:
  - After building pick-value curve, re-calibrate grade breakpoints
  - Target distribution: ~10-15% As, ~10-15% Ds/Fs, bell curve around B/C
  - Use percentile-based grading anchored to expected value by slot
- **Implementation**:
  - Run ablation study: recalculate grades with (a) no risk, (b) no scarcity, (c) 24/24 baselines
  - Show delta analysis: "Scarcity component added +5 pts to grade"
  - Proves each component adds signal
- **Impact**: MEDIUM - More defensible grading scale
- **Effort**: 3-4 hours
- **Status**: 🟡 MEDIUM

**12. Weekly Replacement Level Variant (Optional Advanced)** 🗓️

- **Issue**: Season-long replacement ignores bye weeks and streaming behavior
- **Enhancement**:
  - Add weekly replacement variant where VOR = sum of (weekly_points - weekly_replacement_at_position)
  - Baseline = best plausible streamer available that week
  - Highlights true value of reliable starters at scarce positions vs streamable depth
- **Implementation**:
  - New model: `int_player_weekly_vor.sql`
  - New field: `vor_weekly` (sum of weekly deltas vs dynamic replacement)
  - Comparison report: `vor_seasonal` vs `vor_weekly`
- **Impact**: LOW-MEDIUM - Advanced metric, useful for shallow benches
- **Effort**: 6-8 hours
- **Status**: 🟢 NICE TO HAVE (v1.3.0+)

#### TECHNICAL DEBT & VALIDATION

**13. Composite Luck Weight Validation** 🎲

- **Issue**: Currently using 0.6 schedule / 0.4 scoring timing weights without empirical justification
- **Fix**: Two options:
     1. Variance decomposition: regress wins on schedule vs scoring components; weight ∝ variance explained
     2. Cross-validated correlation: pick weights that best predict rest-of-season wins
- **Implementation**:
  - New notebook: `analysis/luck_weight_calibration.ipynb`
  - Run both methods, document findings
  - If empirical weights differ significantly, update `fct_luck_analysis.sql`
- **Impact**: LOW-MEDIUM - Refinement of already-sound approach
- **Effort**: 2-3 hours
- **Status**: 🟢 NICE TO HAVE

**14. Enhanced Volatility Metrics** 📊

- **Current**: Using CV (coefficient of variation) only
- **Add**:
  - % Top-12 weeks (boom frequency)
  - % Sub-replacement weeks (bust frequency)
  - These are intuitive and capture tail behavior
- **Note**: Already partially implemented (boom/bust rates exist)! Just need to surface in final reports.
- **Effort**: 1 hour
- **Status**: 🟢 QUICK WIN

**15. Injury Treatment: Snaps-Based Availability** 🏥

- **Current**: Using games played for availability
- **Enhancement**: Where possible, use snaps-played share
- **Rationale**: Playing 20% of snaps ≠ full availability
- **Implementation**: Requires snap count data from Sleeper/external API
- **Impact**: LOW-MEDIUM - More precise availability metric
- **Effort**: 4-5 hours (depends on data availability)
- **Status**: 🟢 FUTURE (v1.3.0+)

#### DOCUMENTATION & EXPLAINABILITY

**16. Add Explainability One-Liners** 💬

- **Add**: For each pick, generate 1-sentence explanation
- **Example**: "Round 6 WR outperformed replacement by 38 points, low volatility, +14 vs pick EV → A-"
- **Implementation**:
  - New field: `grade_explanation` in `fct_draft_analysis`
  - Use CASE statements to build natural language summary
- **Impact**: MEDIUM - User comprehension and trust
- **Effort**: 2-3 hours
- **Status**: 🟡 MEDIUM

**17. Zero-Sum Validation with Tolerances** ✅

- **Current**: Zero-sum checks exist but lack explicit tolerances
- **Enhancement**: Add `assert |sum| < 1e-6` with helpful error messages
- **Example**: "Total league luck sums to 0.02 wins (tolerance: 1e-6) - check rounding"
- **Implementation**: Update existing tests with explicit tolerances
- **Effort**: 30 minutes
- **Status**: 🟢 QUICK WIN

#### DELIVERABLES (Publication-Ready Artifacts)

**18. Parameter Freeze System** 📋

- **File**: `data/draft_day_parameters_2025.yml`
- **Contents**:

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

- **Status**: 🔴 REQUIRED FOR #6

**19. FLEX Simulation Report (One-Pager)** 📄

- **Document**: `docs/FLEX_SIMULATION_COMPARISON.md`
- **Contents**:
  - Table: FLEX composition by method (Projection-optimal vs ADP-driven)
  - Chosen baseline with justification
  - Sensitivity analysis: How replacement levels change with different assumptions
- **Status**: 🟡 REQUIRED FOR #7

**20. Pick Value Curve Notebook** 📈

- **File**: `analysis/pick_value_curve_calibration.ipynb`
- **Produces**:
  - Expected VOR by pick number (smooth LOESS curve)
  - Residuals plot (actual - expected)
  - Curve parameters for use in opportunity cost calculations
- **Status**: 🟡 REQUIRED FOR #9

**21. Uncertainty Visualization Suite** 📊

- **Outputs**:
  - Luck: Distribution of simulated wins per team (fan chart)
  - VOR: Bootstrap confidence bands for top 30 players
  - Draft Grades: Grade ranges with uncertainty ribbons
- **Implementation**: New Streamlit dashboard sections or static report images
- **Status**: 🟡 REQUIRED FOR #10

**22. Ablation Study Report** 🔬

- **Analysis**: Recompute draft grades with:
  - (a) No risk adjustment
  - (b) No scarcity multipliers
  - (c) RB24/WR24 baselines (no FLEX simulation)
- **Output**: Delta table showing how each component affects grades
- **Purpose**: Proves each methodological component adds signal
- **Status**: 🟡 REQUIRED FOR #11

#### ACCEPTANCE TESTS (Publication Readiness)

**23. New Test Suite** ✅

- `test_draft_parameters_frozen.sql` - Verify draft grades don't change when new weeks added
- `test_flex_simulation_convergence.sql` - FLEX composition stable across reasonable projection sets
- `test_flex_sanity_ppr.sql` - With PPR, WR takes ≥50% FLEX; TE ≤5% (non-premium)
- `test_risk_factors_valid_range.sql` - All risk factors in [0.0, 1.0]
- `test_luck_monte_carlo_convergence.sql` - Luck mean stabilizes by 5k trials (plot running mean)
- `test_zero_sum_with_tolerance.sql` - League-wide luck/skill sums to 0 ± 1e-6
- `test_grade_distribution_sane.sql` - ~10-15% As, ~10-15% Ds/Fs, bell curve
- **Status**: 🟡 BLOCKING FOR PUBLICATION

---

### Other Analytics Features

24. **Strength of Schedule Analysis** 📊

- Track opponent difficulty over time
- New model: `dbt/models/marts/fct_strength_of_schedule.sql`
- Calculate average opponent win%
- Show remaining opponent strength
- Impact: Medium - Explains why some teams have harder schedules
- Complexity: Low (2 hours)

8. **Injury Impact & Bad Luck Analysis** 🚑 **[NEW - HIGH PRIORITY]**
   - Quantify how injuries have affected each team
   - New models:
     - `dbt/models/staging/stg_player_injuries.sql` - Player injury data from Sleeper
     - `dbt/models/marts/fct_injury_impact.sql` - Games missed, points lost per team
     - `dbt/models/marts/fct_bad_luck_rankings.sql` - "Unluckiest Team" rankings
   - Metrics tracked:
     - **Games Missed**: Total games lost to injury per team
     - **Points Missed**: Projected points lost (based on player's season avg)
     - **Draft Capital Lost**: ADP/draft position of injured players
     - **Injury Severity Score**: Weighted by player quality + games missed
     - **Bad Luck Index**: Composite score ranking teams by injury misfortune
   - Data sources:
     - Sleeper API: Player injury status (IR, Out, Doubtful)
     - Player stats: Season averages for projection
     - Draft data: Original draft position/ADP
   - Impact: **VERY HIGH** - Everyone wants to complain about injuries!
   - Complexity: Medium-High (6-8 hours)
     - Requires new Sleeper API endpoints for injury data
     - Math for projecting "lost points" is non-trivial
     - Need historical player performance data

9. **Draft Performance Analysis** 📊 **[NEW - HIGH PRIORITY]**
   - Compare draft picks to current player rankings
   - New models:
     - `dbt/models/staging/stg_draft_picks.sql` - Draft results from Sleeper
     - `dbt/models/staging/stg_player_rankings.sql` - Current season rankings
     - `dbt/models/marts/fct_draft_analysis.sql` - Draft pick value analysis
   - Metrics calculated:
     - **Draft Position vs. Current Rank**: "Ja'Marr Chase: Drafted 1.01, Currently WR10/Overall 20"
     - **Pick Value Score**: How much better/worse than draft slot
     - **Positional Accuracy**: Did you draft WR1 or WR10?
     - **Hits & Busts**: Players outperforming/underperforming by >10 spots
     - **Draft Grade by Manager**: Overall draft performance score
     - **Best/Worst Pick**: Biggest steal and biggest bust per team
     - **Round Analysis**: Which rounds did you hit/miss on?
   - Visualizations:
     - Draft board heatmap (red = bust, green = hit)
     - Scatter plot: Draft position vs. Current rank
     - Manager draft grade report card
   - Impact: **VERY HIGH** - Draft analysis is endlessly entertaining
   - Complexity: Medium (5-6 hours)
     - Need draft data from Sleeper API
     - Need current player rankings (external API like FantasyPros?)
     - Math for "value over replacement" calculations

10. **Player-Level Analytics** 🏈
    - Track individual player performance across rosters
    - New staging: `dbt/models/staging/stg_player_stats.sql`
    - Track player points, starts, benchings
    - Identify best/worst draft picks
    - Impact: HIGH - Most requested feature
    - Complexity: High (8-10 hours, requires new API endpoints)

11. **Trade Analyzer** 🤝
    - Evaluate trade fairness using historical data
    - New feature: `analytics/trade_analyzer.py`
    - Input: proposed trade details
    - Output: value analysis, historical performance comparison
    - Impact: Medium - Fun but not critical
    - Complexity: Medium (4-5 hours)

### Notifications & Automation

10. **Weekly Email/Slack Notifications** 📧
    - **Status**: Already implemented in `scripts/generate_report.py`!
    - Just needs environment variables configured:

      ```bash
      export EMAIL_SENDER="your-email@gmail.com"
      export EMAIL_PASSWORD="your-app-password"
      # OR
      export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
      ```

    - Impact: HIGH - Automatic engagement, no manual sharing needed
    - Complexity: LOW (30 minutes - just configuration)

---

## 🔐 Version 1.2.0 - Security & Infrastructure (Q1 2025)

### Security Hardening

11. **Dependency Vulnerability Scanning**
    - Add `safety` to GitLab CI pipeline
    - Automated security checks on every commit
    - Alert on known vulnerabilities
    - Effort: 1 hour

12. **Secret Scanning Pre-Commit Hook**
    - Add `detect-secrets` to pre-commit
    - Prevent accidental secret commits
    - Create `.secrets.baseline` file
    - Effort: 30 minutes

13. **Database Backup Strategy**
    - Weekly backups to S3/Google Cloud Storage
    - Incremental backups with retention policy
    - Automated backup script in GitLab schedule
    - Effort: 3-4 hours

### Monitoring & Observability

14. **Error Tracking with Sentry**
    - Add Sentry integration for runtime error tracking
    - Get alerts when dashboard crashes
    - Track error frequency and patterns
    - Effort: 2 hours

15. **Pipeline Failure Notifications**
    - GitLab pipeline failure emails/Slack alerts
    - Data freshness monitoring
    - Alert if pipeline is >1 week behind
    - Effort: 1 hour

16. **Data Freshness Monitoring**
    - Alert if last ingestion was >7 days ago
    - Automatic staleness detection in dashboard
    - "Last updated: X days ago" warning banner
    - Effort: 2 hours

---

## 📈 Version 2.0.0 - Platform Expansion (Q2 2025)

### 📚 Documentation Consolidation

**MAJOR CLEANUP:** Consolidate 23 markdown files → 3 essential docs

**Rationale:** Wait until v2.0.0 to avoid redoing work as features are added in v1.x releases.

**Target Structure:**

1. **`README.md`** (root) - User-facing quick start
   - What is Morgan Bowl?
   - 5-minute setup guide
   - How to use the dashboard
   - Feature highlights (Justice Record, Injury Analysis, Draft Analysis, etc.)
   - Screenshots and examples

2. **`DEVELOPMENT.md`** (root) - Developer/contributor documentation
   - Architecture overview & tech stack
   - Detailed development setup
   - DBT guide and model documentation
   - Testing strategy
   - CI/CD pipeline explanation
   - Release process
   - Roadmap (current + future)

3. **`CHANGELOG.md`** (root) - Version history
   - Keep standard changelog format
   - Include release notes inline (not separate files)
   - Links to detailed feature specs if needed

**Archive to `docs/archive/`:**

- Old release notes (RELEASE_1.0.0.md, RELEASE_1.0.1.md, etc.)
- Draft feature specs (FEATURE_SPEC_*.md)
- Learning logs (nice reference material)
- Old reviews (CODE_REVIEW.md, TECH_REVIEW_*.md)

**Delete:**

- Duplicate/outdated setup guides
- Internal planning docs (.organization-summary.md, NEXT_STEPS.md)

**Impact:** Clean, professional first impression. New contributors/users find what they need immediately.

**Effort:** 4-6 hours (careful merging of content, updating references)

---

### Data Quality & Consistency

17. **DBT Semantic Layer**
    - Define reusable metrics (win%, points per game, etc.)
    - Prevent calculation duplication across models
    - Single source of truth for metric definitions
    - Effort: 4-6 hours

18. **Historical Data Consistency Tests**
    - Ensure past weeks' data never changes
    - Checksum verification for completed weeks
    - Alert if historical data is modified
    - Effort: 3 hours

19. **Advanced DBT Testing**
    - Custom data quality tests (outlier detection)
    - Cross-model relationship tests
    - Data distribution tests (e.g., scores should be 80-200)
    - Effort: 4 hours

### Performance & Scalability

20. **Query Performance Optimization**
    - Create denormalized dashboard summary view
    - Add database indexes for common queries
    - Implement query result caching
    - Effort: 3-4 hours

21. **Multi-League Support**
    - Parameterize league configuration
    - Support multiple fantasy leagues in one database
    - League selector in dashboard
    - Effort: 8-10 hours (major feature)

22. **Mobile-Responsive Dashboard**
    - Optimize Streamlit dashboard for mobile
    - Responsive layouts for phone screens
    - Touch-friendly controls
    - Effort: 4-5 hours

---

## 🎨 Version 3.0.0 - Premium Features (Future)

### Advanced Analytics

23. **Machine Learning Predictions**
    - Predict weekly matchup outcomes
    - Player performance forecasting
    - Draft pick value predictions
    - Effort: 20+ hours (research + implementation)

24. **Custom Scoring Systems**
    - Support different league scoring rules
    - What-if analysis for scoring changes
    - Historical re-scoring with different rules
    - Effort: 6-8 hours

25. **Waiver Wire Recommendations**
    - Analyze available players
    - Recommend pickups based on team needs
    - Projected impact analysis
    - Effort: 10-12 hours

### Social Features

26. **League Chat Integration**
    - Display Sleeper league chat messages
    - Sentiment analysis on trash talk
    - "Most active trash talker" award
    - Effort: 6-8 hours

27. **Historical Season Comparison**
    - Multi-season database
    - Year-over-year performance tracking
    - Dynasty league support
    - Effort: 8-10 hours

---

## 🏆 Recommended Priority Order

### CRITICAL - Draft Analysis Methodology Fixes (DO FIRST) 🚨

**Before publishing any draft analysis results, these MUST be completed:**

1. 🔴 **Fix Look-Ahead Bias (#6)** - 6-8 hours - **BLOCKING**
   - Draft grades currently use post-draft information (scientifically invalid)
   - Create parameter freeze system, separate draft-day from realized value

2. 🔴 **FLEX Projection-Based (#7)** - 3-4 hours - **BLOCKING**
   - Switch from ADP-based to projection-based FLEX simulation
   - Changes replacement levels for accurate VOR

3. 🟡 **Multiplicative Risk Model (#8)** - 4-5 hours - **HIGH**
   - Replace averaged penalties with multiplicative risk factors
   - Add position-specific priors (RBs more fragile than QBs)

4. � **Pick-Value Curve (#9)** - 5-6 hours - **HIGH**
   - Fit expected value by draft pick curve
   - Enables proper cross-positional opportunity cost

5. 🟡 **Uncertainty Quantification (#10)** - 4-5 hours - **MEDIUM**
   - Add confidence intervals for luck, VOR, grades
   - Prevents false precision, communicates statistical rigor

**Total Effort**: 22-32 hours
**Payoff**: Transforms draft analysis from "interesting" to "publication-ready"
**Current Grade**: B+ → **Target Grade**: A

### Immediate (This Week)

1. ✅ Version 1.0.1 - COMPLETED (Oct 19, 2025)
2. ✅ Version 1.1.0 - COMPLETED (Oct 19, 2025) - Universal League Configuration

### Short Term (Next 2-4 Weeks) - v1.2.0

3. 📊 **Draft Analysis Methodology Fixes (#6-10)** - See critical section above (22-32 hours)
4. 🚑 **Injury Impact Analysis (#25)** - League mates will love this (6-8 hours)
5. 📊 **Strength of Schedule (#24)** - Easy analytics win (2 hours)
6. 📧 **Enable notifications** - Already coded, just needs env vars! (30 min)

### Deferred Features

- 🎲 **Playoff Probability Simulator** - Postponed (complex, less immediate value)
  - Will revisit in v1.2.0 or v2.0.0
  - Focus on league portability and core analytics first

### Medium Term (Next Quarter)

7. 🏈 Player analytics (#11)
8. 🔐 Security hardening
9. 📈 Monitoring setup

### Long Term (6+ Months) - v2.0.0

10. � Documentation consolidation (23 files → 3)
11. 🌐 ESPN/Yahoo league import
12. 📊 DBT semantic layer
13. 🤖 ML predictions

---

## 📊 Impact vs. Effort Matrix

### Quick Wins (High Impact, Low Effort)

- 🌍 **Universal League Config (#1)** - 4-6 hours - **DO THIS FIRST!**
- 📧 Email/Slack notifications (#10) - 30 min (already coded!)
- 📊 Strength of schedule (#6) - 2 hours

- 📧 Email/Slack notifications (#12) - 30 min
- 🟡 Fix hardcoded year (#4) - 15 min
- 🟡 Markdown linting (#5) - 30 min
- 📊 Strength of schedule (#7) - 2 hours

### Major Projects (High Impact, High Effort) ⭐ **NEW FEATURES**

- 🚑 **Injury Impact & Bad Luck Rankings (#8)** - 6-8 hours - **DO THIS FIRST!**
- 📊 **Draft Performance Analysis (#9)** - 5-6 hours - **DO THIS SECOND!**
- 🎲 Playoff simulator (#6) - 3-4 hours
- 🏈 Player analytics (#10) - 8-10 hours
- 🌐 Multi-league support (#23) - 8-10 hours

### Fill Projects (Low Impact, Low Effort)

- 🔐 Secret scanning (#14) - 30 min
- 📈 Data freshness alerts (#18) - 2 hours

### Thankless Tasks (Low Impact, High Effort)

- 🤖 ML predictions (#25) - 20+ hours (save for later)

---

## 📝 Notes

**Last Updated**: October 19, 2025
**Current Version**: 1.1.0 ✅
**Next Release**: 1.2.0 (Draft Analysis Methodology Fixes + Advanced Analytics)
**Target for 2.0.0**: Q2 2025 (after feature set matures)

**🚨 CRITICAL PRIORITY - Draft Analysis Peer Review (Oct 19, 2025)**:

Received expert technical review identifying **methodological issues** in draft analysis:

- **Current Grade**: B+ (solid foundations, publishable with fixes)
- **Blocking Issues**: Look-ahead bias, ADP-based FLEX, averaged risk penalties
- **Target Grade**: A (publication-ready for Fantasy Football Analytics journals)
- **Effort Required**: 22-32 hours of methodology fixes
- **Impact**: Transforms draft analysis from "fun internal tool" to "research-grade system"

**Key Strengths Identified**:

- ✅ Clear luck vs skill decomposition
- ✅ Monte Carlo simulation for expected wins
- ✅ FLEX replacement via simulation (correct approach)
- ✅ Process vs outcome separation (draft-day vs hindsight)
- ✅ Zero-sum validations

**Critical Fixes Required (BLOCKING)**:

1. 🔴 Fix look-ahead bias - Draft grades use post-draft data (scientifically invalid)
2. 🔴 FLEX projection-based - Switch from ADP to projections for replacement levels
3. 🟡 Multiplicative risk model - Replace averaging with position-aware multiplication
4. 🟡 Pick-value curve - Add proper opportunity cost anchoring
5. 🟡 Uncertainty quantification - Add CIs everywhere to prevent false precision

**Recommended Next Steps**:

1. Create draft-day parameter freeze (YAML snapshot of projections, replacements, scarcity)
2. Rerun FLEX simulation with projected PPG instead of ADP
3. Implement multiplicative risk: `Availability × Volatility × Position_Prior`
4. Fit LOESS curve for expected value by pick number
5. Add bootstrap CIs for VOR, MC distributions for luck

**See**: Draft Analysis Methodology Improvements section above for full details

---

**Development Philosophy**:

- **Quality over speed** - Take time to learn DataOps patterns correctly
- **Test-driven** - Write tests for all fixes and features
- **Document everything** - Before/after examples, learning notes
- **One thing at a time** - Master each concept before moving on
- **Wait to refactor docs** - Let features stabilize before v2.0.0 doc consolidation

**🔥 PRIORITY FEATURES** for v1.2.0:

1. **Draft Analysis Methodology Fixes** - FIX LOOK-AHEAD BIAS & LEAKAGE (22-32 hours) 🚨 **BLOCKING**
2. **Injury Impact Analysis** - Quantify how unlucky each team has been with injuries
3. **Strength of Schedule** - Easy analytics win, useful insights

**⚠️ METHODOLOGY DEBT** (Must fix before publication):

- **Look-ahead bias**: Draft grades currently use post-draft information → scientifically invalid
- **ADP-based FLEX**: Should use projections, not market sentiment → inaccurate replacement levels
- **Averaged risk**: Should be multiplicative with position priors → under/over-discounts
- **No uncertainty**: Point estimates without CIs → false precision
- **Grade calibration**: Need pick-value curve for proper opportunity cost

**Peer Review Score**: B+ → Target: A (publication-ready)

**⏸️ DEFERRED FEATURES**:

- **Playoff Probability Simulator** - Postponed to v1.2.0 or later
  - Reason: Complex implementation, less immediate value than league portability
  - Focus: Build foundation for universal league support first

**📚 DOCUMENTATION STRATEGY**:

- **v1.x releases**: Keep adding to existing docs as needed (don't worry about duplication)
- **v2.0.0**: Major documentation consolidation (23 files → 3 essential docs)
- **Rationale**: Avoid redoing documentation work as features evolve

**🌐 LONG-TERM VISION**:

- **v2.0.0**: ESPN & Yahoo league import (unified fantasy platform analytics)
- **Platform-agnostic**: Work with any fantasy football league, any platform

**Release Strategy**:

- ✅ **v1.0.1** (Oct 19, 2025): Critical security & quality fixes - SHIPPED!
- 🎯 **v1.1.0** (Next): Advanced analytics (injury impact, draft analysis, playoff simulator)
- 📈 **v2.0.0** (Q2 2025): Documentation consolidation + platform expansion features

**Quick Win Alert**: Feature #12 (Email/Slack notifications) is already coded! Just needs environment variables set up. This is the highest ROI feature available right now.
