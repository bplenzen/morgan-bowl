# Code Review Summary & Next Steps

## What You Have Now

✅ **21 Self-Contained Prompt Files** in `prompts/` directory
✅ **Progress Tracker** (`CODE_REVIEW_PROGRESS.md`)
✅ **Automation Scripts** (`scripts/next_task.sh`, `scripts/mark_done.sh`)
✅ **Complete System** for zero-overhead code review implementation

## Your Zero-Overhead Workflow

### Every Time You Work on Code Review

```bash
# Step 1: Get next task (auto-displays prompt)
./scripts/next_task.sh

# Step 2: Copy output, paste into NEW Claude Code chat

# Step 3: Let Claude Code work (it has full context in prompt)

# Step 4: After Claude finishes, mark complete
./scripts/mark_done.sh 1

# Step 5: Repeat!
```

**That's it!** No context switching, no manual tracking, no wondering "where was I?"

## What's in Each Prompt File

Each prompt is **completely self-contained**:

✅ Problem description + exact file locations
✅ Why it matters (impact)
✅ Exact code to fix (with examples)
✅ Step-by-step instructions
✅ Completion checklist
✅ Validation queries
✅ Next step reminder

**You never need to reference the original code review.**

## Priority & Time Estimates

### 🚨 Critical Issues (Must Fix First) - ~2-3 hours

1. **VOR Calculation Bug** - BLOCKING all other work (30 min)
2. **Risk Tier Mismatch** - Breaking draft grades (20 min)
3. **Hardcoded League Size** - Wrong pick-value curve (20 min)

### ⚠️ Warnings (Should Fix) - ~3-4 hours

4. Rename "Monte Carlo" model (15 min)
5. K/DEF UI inconsistency (30 min)
6. Sample size for uncertainty (15 min)
7. Crude PPG estimates (45 min)
8. Trade tracking limitation (30 min)

### 💡 Suggestions (Nice to Have) - ~10-15 hours

9. Boris Chen tier visualizations (1 hour)
10. Playoff probability calculator (2 hours)
11. Spike weeks metric (1 hour)
12. ROS rankings (2 hours)
13. Luck formula documentation (30 min)
14. Uncertainty toggle default (15 min)
15. Trade analyzer (2 hours)
16. FantasyPros API integration (1.5 hours)
17. EPA framework (2 hours)
18. Playoff SOS (1 hour)
19. Target share metrics (1.5 hours)
20. Player comparisons (2 hours)
21. Waiver wire heatmaps (1.5 hours)

## Recommended Approach

### Week 1: Fix Critical Bugs (Must Do)

```bash
./scripts/next_task.sh  # Start with #1
# Work through #1-3
```

**After Week 1**: All critical data bugs are fixed. Dashboard works correctly.

### Week 2: Fix Warnings (Should Do)

```bash
# Continue with #4-8
```

**After Week 2**: Data quality is excellent, UX is clean.

### Weeks 3-4: Add Enhancements (Optional)

```bash
# Pick and choose from #9-21 based on interest
```

**After Week 4**: Industry-leading fantasy analytics platform!

## File Structure Created

```
morgan-bowl/
├── CODE_REVIEW_PROGRESS.md          # Your progress tracker
├── REVIEW_SUMMARY.md                # This file
├── prompts/
│   ├── README.md                    # Prompts directory guide
│   ├── 01_vor_calculation_bug.md    # Critical #1
│   ├── 02_risk_tier_mismatch.md     # Critical #2
│   ├── 03_hardcoded_league_size.md  # Critical #3
│   ├── 04_rename_monte_carlo.md     # Warning #4
│   ├── ...                          # (prompts 5-20)
│   └── 21_waiver_heatmaps.md       # Suggestion #21
└── scripts/
    ├── next_task.sh                 # Auto-show next prompt
    └── mark_done.sh                 # Mark task complete
```

## Key Benefits of This System

✅ **No Mental Overhead**: Script tells you exactly what to do next
✅ **No Context Switching**: Each prompt is self-contained
✅ **No Manual Tracking**: Scripts update progress automatically
✅ **One Problem Per Chat**: Clean separation of concerns
✅ **Copy-Paste Ready**: Just paste into Claude Code and go
✅ **Verifiable Progress**: Clear checklist in `CODE_REVIEW_PROGRESS.md`

## Example Session

```bash
$ ./scripts/next_task.sh
📋 Next task: #1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fix Critical Bug: VOR Calculation Uses ADP as PPG
[... full prompt displays ...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ After completing, run: ./scripts/mark_done.sh 1

# [You copy-paste prompt into Claude Code]
# [Claude Code fixes the bug]
# [You verify it works]

$ ./scripts/mark_done.sh 1
✅ Task #1 marked complete

🔜 Next task:
📋 Next task: #2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fix Critical Bug: Risk Tier Naming Mismatch
[... next prompt auto-displays ...]
```

## Testing Your Fixes

After each critical fix (#1-3):

```bash
cd dbt
poetry run dbt build --select <model_name>
poetry run dbt test
```

After all critical fixes:

```bash
make test
poetry run streamlit run analytics/dashboard.py
```

## When You're Done

After completing all tasks:

1. ✅ Run full test suite:

   ```bash
   make test
   cd dbt && poetry run dbt test
   ```

2. 🎉 Launch dashboard and verify everything works:

   ```bash
   poetry run streamlit run analytics/dashboard.py
   ```

3. 📝 Consider documenting your improvements:
   - Blog post about the analytics methodology
   - Tweet thread about the build
   - Post to /r/fantasyfootball

4. 🚀 Open source it (optional):
   - Your anti-look-ahead bias methodology is publication-worthy
   - Uncertainty quantification is rare in fantasy tools
   - Could help thousands of leagues

## Questions?

Each prompt has:

- Exact file locations
- Code snippets
- Validation queries
- Completion criteria

Just paste into Claude Code and let it work!

## Start Now

```bash
./scripts/next_task.sh
```

Copy the output, paste into a fresh Claude Code chat, and you're off! 🚀

---

**Generated**: 2025-11-01
**Total Prompts**: 21 (3 critical, 5 warnings, 13 suggestions)
**Estimated Critical Fixes**: 2-3 hours
**Estimated All Fixes**: ~18 hours
