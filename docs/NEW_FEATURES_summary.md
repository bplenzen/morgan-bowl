# New Features Added to Roadmap

**Date**: October 19, 2025
**Author**: Ben

## Summary

Two new high-priority features have been added to the Morgan Bowl roadmap based on league engagement needs.

## Features Added

### 🚑 Feature #8: Injury Impact & Bad Luck Analysis

**What it does**: Quantifies how injuries have affected each team and ranks teams by "bad luck"

**Why it's awesome**:

- Everyone complains about injuries - now they have data to prove it!
- Shows games missed, points lost, draft capital wasted
- Creates "Unluckiest Team" rankings

**Key Metrics**:

- **Games Missed**: Count of player-weeks lost to injury
- **Projected Points Lost**: Estimated points missed (based on player's season average)
- **Draft Capital Lost**: Weighted by where player was drafted (losing a 1st rounder hurts more)
- **Injury Impact Score**: Composite score = severity × points × draft capital
- **Bad Luck Index**: Team-level ranking of injury misfortune

**Example Output**:

```
🚑 Bad Luck Rankings:
1. Ben's Team - 487.3 bad luck index (15 games missed, 212.5 pts lost)
   - Ja'Marr Chase (1.01) - IR for 4 weeks
   - CMC (traded for) - Out 3 weeks
```

**Effort**: 6-8 hours
**Priority**: Very High

---

### 📊 Feature #9: Draft Performance Analysis

**What it does**: Compares draft picks to current player rankings and grades each manager's draft

**Why it's awesome**:

- Endless roasting material for bad picks
- See who drafted "steals" vs "busts"
- Track which rounds you hit/missed on

**Key Metrics**:

- **Pick Value Score**: Current rank - Draft position
  - Example: Ja'Marr Chase drafted 1.01, currently WR10/Overall #20 → Score: +19 (bust)
  - Example: Puka Nacua drafted 8.03, currently WR6/Overall #15 → Score: -32 (steal!)
- **Draft Grade**: Letter grade (A-F) based on average pick value
- **Hit Rate**: % of picks that outperformed expectations
- **Best/Worst Pick**: Biggest steal and biggest bust per manager

**Example Output**:

```
📊 Draft Grades:
1. Sarah - Grade: A (Best: Puka Nacua 8.03, Worst: Kelce 2.12)
2. Mike - Grade: B+ (Best: Breece Hall 1.04, Worst: DJ Moore 4.04)
3. Ben - Grade: C (Best: Tank Dell 7.01, Worst: Ja'Marr 1.01) ⚠️
```

**Effort**: 5-6 hours
**Priority**: Very High

---

## Implementation Plan

### Phase 1: Data Collection (Week 1)

1. Add Sleeper API endpoints:
   - Draft data (`GET /v1/draft/{draft_id}`)
   - Player injury status (from roster data)
   - Player season stats
2. Create staging models for raw data
3. Test data quality

### Phase 2: Injury Analysis (Week 2)

1. Build `fct_injury_impact.sql` model
2. Build `fct_bad_luck_rankings.sql` model
3. Add injury section to weekly report
4. Create dashboard visualizations

### Phase 3: Draft Analysis (Week 3)

1. Build `fct_draft_analysis.sql` model
2. Build `fct_draft_grades.sql` model
3. Add draft section to weekly report
4. Create draft visualizations

### Phase 4: Polish & Deploy (Week 4)

1. DBT tests for data quality
2. Error handling
3. Documentation
4. Share with league! 🎉

---

## Recommended Priority

**Do these AFTER critical fixes (#1-2) but BEFORE other features**

Reasoning:

- ✅ High engagement (everyone loves injury/draft talk)
- ✅ Relatively quick to implement (5-8 hours each)
- ✅ Unique insights (not available elsewhere)
- ✅ Great for weekly reports
- ✅ Roasting material for league chat

---

## Files Created

- `docs/FEATURE_SPEC_injury_analysis.md` - Complete spec for injury feature
- `docs/FEATURE_SPEC_draft_analysis.md` - Complete spec for draft feature
- `docs/ROADMAP.md` - Updated with new features

## Next Steps

1. Review feature specs
2. Confirm Sleeper API has necessary data
3. Start with critical fixes (#1-2)
4. Then implement injury analysis (#8)
5. Then implement draft analysis (#9)
6. Profit from league mates' amazement! 🏆
