# Deprecated Models

This document tracks models that are deprecated but kept for backward compatibility.

## fct_justice_record.sql

**Deprecated:** October 19, 2025
**Replaced by:** `fct_advanced_luck.sql`

### Reason for Deprecation

The "justice record" approach used a simple median-based methodology:

- Top 6 scorers each week = justice win
- Bottom 6 scorers = justice loss
- Luck = actual wins - justice wins

This was easy to understand but statistically weak.

### Why fct_advanced_luck is Better

The advanced luck model uses more sophisticated metrics:

1. **All-Play Record**: If you played every team each week, what would your record be?
2. **Expected Wins**: All-play win% × games played = more accurate luck measure
3. **Schedule Strength**: Did you face opponents on their hot/cold weeks?
4. **Close Game Performance**: Games within 10 points are essentially coin flips
5. **Composite Luck Score**: Weighted combination of all factors (0-100 scale)

### Migration Path

- ✅ Dashboard updated to use fct_advanced_luck (Oct 19, 2025)
- ⏳ Model still builds to avoid breaking CI/CD
- ⏳ Can be fully removed in v2.0.0 after confirming no external dependencies

### If You Need to Restore Justice Record

If for some reason you want the old approach back:

1. The model still exists and builds successfully
2. The dashboard function `load_justice_record()` still works
3. Just add the page back to the navigation menu in `analytics/dashboard.py`
