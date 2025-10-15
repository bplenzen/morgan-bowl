# dbt Project Scaffold

This directory houses the dbt project that will model Sleeper ingestion outputs stored in DuckDB.

## Structure

- `dbt_project.yml` – project configuration (profile name, paths, default schemas).
- `models/` – dbt models, separated into `staging/` (views over raw tables) and `marts/` (fact/dimension tables).
- `macros/`, `tests/`, `seeds/`, `snapshots/`, `analysis/` – placeholders for future expansion.

## Next Steps

1. Copy `profiles.example.yml` to your local `~/.dbt/profiles.yml` (or configure environment variable `DBT_PROFILES_DIR`) and update the path to the DuckDB file.
2. Define sources for the `staging` schema (league, users, rosters, matchups, transactions).
3. Build staging models that standardize field names and types before creating marts.
