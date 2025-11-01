# Fix Warning: Rename "Monte Carlo" Model (Misleading Name)

## Problem

The file `dbt/models/intermediate/int_monte_carlo_expected_wins.sql` claims to use "Monte Carlo simulation" but actually uses **Wilson score intervals** (closed-form binomial approximation).

From the file header (lines 1-10):

```sql
-- Monte Carlo simulation for expected wins uncertainty quantification
-- Approach: Simulate N random schedules per team, calculate wins distribution
```

But the actual implementation (lines 68-143) uses Wilson score intervals:

```sql
-- Wilson score interval for 95% confidence
-- Formula: p ± z * sqrt(p*(1-p)/n) where z=1.96 for 95% CI
```

There is **no random sampling, no simulation, no Monte Carlo Markov Chain** - just a closed-form statistical formula.

## Impact

- Academically dishonest (would get flagged in peer review)
- Misleading to users and future maintainers
- Wilson score intervals are great! Just incorrectly named.

## Required Fix

Rename the model to accurately describe what it does: calculate binomial confidence intervals using Wilson score method.

## Solution

1. Rename the file: `int_monte_carlo_expected_wins.sql` → `int_expected_wins_uncertainty.sql`
2. Update the file header to accurately describe the methodology
3. Update all references in downstream models

## Task

1. **Rename the SQL file:**

   ```bash
   cd dbt/models/intermediate
   git mv int_monte_carlo_expected_wins.sql int_expected_wins_uncertainty.sql
   ```

2. **Update the file header** in `int_expected_wins_uncertainty.sql`:

   ```sql
   {{ config(materialized='table') }}

   -- Expected Wins Uncertainty Quantification
   -- Uses Wilson score intervals (binomial confidence intervals) to estimate
   -- uncertainty in expected wins calculations.
   --
   -- Methodology: Closed-form binomial CI (NOT Monte Carlo simulation)
   -- - Point estimate: All-play win percentage × games played
   -- - Confidence interval: Wilson score method (handles small samples)
   -- - Output: p05, p50, p95 percentiles with standard error
   ```

3. **Update downstream references** in `fct_advanced_luck.sql`:
   - Line 148: Change `{{ ref('int_monte_carlo_expected_wins') }}` to `{{ ref('int_expected_wins_uncertainty') }}`

4. **Run DBT:**

   ```bash
   cd dbt
   poetry run dbt build --select int_expected_wins_uncertainty fct_advanced_luck
   poetry run dbt test
   ```

## Completion Criteria

- [ ] File renamed to `int_expected_wins_uncertainty.sql`
- [ ] File header accurately describes Wilson score interval methodology
- [ ] All references updated in downstream models
- [ ] All DBT tests pass
- [ ] No mentions of "Monte Carlo" in the model (except to clarify it's NOT MC)

## Optional Enhancement

Add a comment explaining why Wilson score is better than normal approximation for small samples:

```sql
-- Why Wilson score instead of normal approximation?
-- - Handles small sample sizes (n < 30) correctly
-- - Prevents invalid CIs (won't go below 0 wins or above n games)
-- - Symmetric for p ≈ 0.5, adjusts for extreme probabilities
-- - Industry standard for binomial proportions (Brown et al. 2001)
```

---

**After completing this task:**

1. Mark #4 as done in `CODE_REVIEW_PROGRESS.md`
2. Run `./scripts/mark_done.sh 4` (or manually update)
3. Move to prompt #5
