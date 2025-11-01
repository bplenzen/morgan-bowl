# Code Review Progress Tracker

Last updated: 2025-11-01
Current status: Not started

## Critical Issues (Must Fix First)

- [ ] **#1 - VOR Calculation Bug** - int_player_risk_factors.sql uses ADP as PPG
- [ ] **#2 - Risk Tier Mismatch** - VERY_LOW_RISK vs LOW_RISK naming inconsistency
- [ ] **#3 - Hardcoded League Size** - int_expected_value_by_pick.sql assumes 10 teams

## Warnings (High Priority)

- [ ] **#4 - Rename "Monte Carlo"** - int_monte_carlo_expected_wins.sql isn't actually MC
- [ ] **#5 - K/DEF Inconsistency** - Excluded from grading but shown in UI
- [ ] **#6 - Sample Size for Uncertainty** - Showing CI after only 2 games
- [ ] **#7 - Crude PPG Estimates** - Pick-value curve uses hardcoded tiers
- [ ] **#8 - No Trade Tracking** - Draft grades don't update after trades

## Suggestions (Nice to Have)

- [ ] **#9 - Boris Chen Tiers** - Add color-coded tier visualizations
- [ ] **#10 - Playoff Probability** - Add "67% to make playoffs" calculator
- [ ] **#11 - Spike Weeks** - Add JJ Zachariason's top-12 weeks metric
- [ ] **#12 - ROS Rankings** - Show rest-of-season projections
- [ ] **#13 - Luck Formula Docs** - Link to calibration notebook
- [ ] **#14 - Uncertainty Toggle** - Default to ON instead of OFF
- [ ] **#15 - Trade Analyzer** - Add trade evaluation tool
- [ ] **#16 - FantasyPros API** - Integrate consensus projections
- [ ] **#17 - EPA Framework** - Add expected points vs actual points
- [ ] **#18 - Playoff SOS** - Add strength of schedule for weeks 15-17
- [ ] **#19 - Target Share** - Add opportunity metrics for WR/TE
- [ ] **#20 - Player Comps** - Add similarity scores
- [ ] **#21 - Waiver Heatmaps** - Analyze add/drop ROI

---

**Next task to work on:** #1 (see prompts/ directory)

## Usage

```bash
# Get next prompt
cat prompts/01_vor_calculation_bug.md

# After completing task #1, mark as done
sed -i '' 's/- \[ \] \*\*#1/- [x] **#1/' CODE_REVIEW_PROGRESS.md

# Or use helper scripts (see scripts/ directory)
./scripts/next_task.sh
./scripts/mark_done.sh 1
```
