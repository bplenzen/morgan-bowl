# MVP Analytics Views

The initial analytics slice focuses on three deliverables mapped directly to dbt models:

## League Standings
- **Source**: `analytics.fct_standings`
- **Fields**: wins, losses, win_pct, points_for, points_against, point_diff, manager_name.
- **Dashboard ideas**: league table sorted by win_pct, sparkline of point_diff, filters by manager.

## Matchup View
- **Source**: `analytics.fct_matchups`
- **Fields**: week, roster_id, manager_name, points, opponent points, win_flag, point_diff.
- **Dashboard ideas**: week selector showing both sides of each matchup, highlight blowouts via point_diff.

## Team View
- **Source**: combine `analytics.fct_standings` with roster metadata from `staging.stg_rosters` and `staging.stg_users`.
- **Fields**: roster owner, current players array, cumulative points, record summary.
- **Dashboard ideas**: per-team detail page with player list, trend of weekly points (use fct_matchups).

These views are intentionally lightweight—once they are visualized in Metabase/Lightdash we can iterate on more advanced analyses (transactions, waiver efficiency, projection deltas).
