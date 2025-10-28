## Summary
<!-- What problem does this PR solve? Keep it tight and business-focused. -->

## Linked Issue(s)

- Closes #

## Type

- [ ] Feature
- [ ] Fix
- [ ] Refactor
- [ ] Docs
- [ ] Chore (deps/tooling)
- [ ] Data/DBT only

## Scope of Change

- Python: `morgan_bowl/` modules touched:
- dbt: models/seeds/snapshots/macros touched:
- App: Streamlit components/pages touched:

## Implementation Notes

- Key design decisions (and why):
- Alternatives considered:

## Data Provenance (CRITICAL: no arbitrary values)

- [ ] No made-up constants, thresholds, or sample data introduced
- [ ] Any new constants documented + justified (link to config, env var, seed, or test)
- [ ] All new SQL uses parameterized queries where applicable

## DuckDB & Streamlit

- [ ] App connections use `duckdb.connect('database.db', read_only=True)`
- [ ] Expensive reads are cached with `@st.cache_data`
- [ ] Connections closed or used via context managers

## DBT Hygiene

- [ ] Models have/update `schema.yml` with `not_null`/`unique`/`relationships` as appropriate
- [ ] `dbt run/test/build` locally successful
- [ ] Sources have freshness (if applicable)
- [ ] Exposures kept in sync with dashboard usage

## API (Sleeper) Reliability

- [ ] Retries/backoff for rate limits
- [ ] Pydantic validation for responses
- [ ] Errors logged with context; no raw stack traces to users

## Security

- [ ] No secrets committed (checked .env, profiles.yml, code)
- [ ] No `shell=True`, unsafe eval/exec, or broad file perms

## Tests & Coverage

- [ ] Unit tests for new/changed logic
- [ ] Integration tests for API/DB where relevant (mock external calls)
- [ ] Coverage gate passes (≥ 80% overall, critical paths covered)
- [ ] Edge cases included (errors, empty data, timeouts)

## Verification Steps (exact commands)

```bash
poetry check && poetry lock --no-update
poetry export -f requirements.txt -o /tmp/reqs.txt

ruff check . && ruff format --check .
mypy --strict morgan_bowl/

pytest -q --maxfail=1 --durations=10 --cov=morgan_bowl --cov-report=term-missing

cd dbt_morgan_bowl
dbt deps && dbt compile && dbt ls
dbt test && dbt build --fail-fast
# optional:
dbt source freshness
dbt docs generate
