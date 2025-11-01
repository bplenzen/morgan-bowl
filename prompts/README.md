# Code Review Prompts

This directory contains **21 self-contained prompts** for fixing issues identified in the comprehensive code review.

## Quick Start

### Option 1: Manual Workflow (Copy-Paste)

```bash
# 1. Check what's next
cat CODE_REVIEW_PROGRESS.md | grep "Next task"

# 2. Read the prompt
cat prompts/01_vor_calculation_bug.md

# 3. Copy to clipboard (macOS)
cat prompts/01_vor_calculation_bug.md | pbcopy

# Or on Linux
cat prompts/01_vor_calculation_bug.md | xclip -selection clipboard

# 4. Paste into new Claude Code chat

# 5. After Claude finishes, update tracker
# Edit CODE_REVIEW_PROGRESS.md and change [ ] to [x] for completed task
```

### Option 2: Automated Workflow (Recommended)

```bash
# 1. Get next prompt (auto-displays + copies to clipboard)
./scripts/next_task.sh

# 2. Paste into new Claude Code chat, let it work

# 3. Mark done and get next prompt
./scripts/mark_done.sh 1

# Repeat!
```

## Workflow Rules

1. **One problem per chat** - Start fresh Claude Code chat for each prompt
2. **No manual tracking** - Scripts handle progress automatically
3. **Sequential order** - Do Critical → Warnings → Suggestions
4. **No context needed** - Each prompt is fully self-contained

## File Structure

```
prompts/
├── README.md                        # This file
├── 01_vor_calculation_bug.md        # Critical Issue #1
├── 02_risk_tier_mismatch.md         # Critical Issue #2
├── 03_hardcoded_league_size.md      # Critical Issue #3
├── 04_rename_monte_carlo.md         # Warning #4
├── ...                              # (prompts 5-21)
└── 21_waiver_heatmaps.md           # Suggestion #21
```

## Priority Order

### 🚨 Critical (Fix First)

- **#1**: VOR calculation bug (BLOCKING - must fix before anything else)
- **#2**: Risk tier naming mismatch
- **#3**: Hardcoded league size

### ⚠️ Warnings (High Priority)

- **#4-8**: Data quality and UX issues

### 💡 Suggestions (Nice to Have)

- **#9-21**: Feature enhancements and industry best practices

## Prompt Template

Each prompt follows this structure:

1. **Problem**: What's wrong + exact file locations
2. **Impact**: Why it matters
3. **Required Fix**: Code changes needed
4. **Task**: Step-by-step instructions
5. **Completion Criteria**: Checklist for "done"
6. **Next Step**: Reminder to update tracker

## Helper Scripts

### `scripts/next_task.sh`

- Finds next uncompleted task
- Displays full prompt
- Shows completion command

### `scripts/mark_done.sh <task_number>`

- Marks task complete in tracker
- Updates "Last modified" date
- Auto-shows next task

## Progress Tracking

Track your progress in `CODE_REVIEW_PROGRESS.md`:

```markdown
## Critical Issues (Must Fix First)

- [x] **#1 - VOR Calculation Bug** ✅ DONE
- [ ] **#2 - Risk Tier Mismatch** ⬅️ NEXT
- [ ] **#3 - Hardcoded League Size**
```

## Tips

- **Work sequentially**: Don't skip Critical issues
- **Test after each fix**: Run `make test` after each prompt
- **One chat per prompt**: Don't combine multiple fixes in one chat
- **Copy-paste exact prompts**: They're optimized for Claude Code

## Estimated Time

- **Critical Issues (1-3)**: ~2-3 hours
- **Warnings (4-8)**: ~3-4 hours
- **Suggestions (9-21)**: ~10-15 hours (optional)

**Total for Critical + Warnings**: ~6 hours
**Total for everything**: ~18 hours

## Need Help?

If a prompt is unclear or you encounter issues:

1. Check the full code review in the original comprehensive analysis
2. Ask Claude Code to explain the issue in more detail
3. Skip to next prompt and come back later

## Celebrate! 🎉

After completing all 21 prompts:

1. Run full test suite: `make test && cd dbt && poetry run dbt test`
2. Launch dashboard: `poetry run streamlit run analytics/dashboard.py`
3. Share your work! Blog post, Twitter, /r/fantasyfootball
4. Consider open-sourcing - this would be valuable to the community

---

**Generated**: 2025-11-01
**Source**: Comprehensive code review by Claude Code expert analyst
