---

### `.github/ISSUE_TEMPLATE/code-review.md`

```md
---
name: Code Review (Evidence-Based)
about: Request a cautious, evidence-based review with file/line citations
labels: review
---

## Context

- Area(s): (ingestion / analytics / app / dbt / tests / infra)
- Goal of review:

## Strict Rules (confirm)

- [ ] No hallucinations: only cite files/lines that exist in this repo
- [ ] Mark uncertainties as “Unknown (no evidence in repo)”
- [ ] Paste repo-search results for each claim

## Findings (use this structure per item)

**[Severity: High/Med/Low] [Category] Short title**

**Evidence**

- `path:line-range` — “quoted snippet…”
- (optional) search hits shown

**Why it matters**

- (impact/risk)

**Recommendation (precise next step)**

- (patch idea, command to run, test to add, dbt test to write, etc.)

## Categories to cover

- Correctness & Dead/Deprecated Code (unused symbols, unreachable paths, old flags)
- Data Provenance & “Random Data” (magic numbers, hard-coded seeds)
- Tests & Coverage (gaps, edge cases, API/DB integration)
- Style & Maintainability (PEP8/Black/ruff/mypy, docstrings, logging)
- Performance (N+1, repeated I/O, DF copies, dbt inefficiency)
- Security & Secrets
- Dependencies & Build (Poetry, dbt packages)
- DuckDB & Streamlit specifics
- CI/CD & Reproducibility

## Verification Plan (commands to run)

```bash
poetry check && poetry lock --no-update
ruff check . && ruff format --check .
mypy --strict morgan_bowl/
vulture morgan_bowl tests
deptry .
pytest -q --maxfail=1 --durations=10 --cov=morgan_bowl --cov-report=term-missing
cd dbt_morgan_bowl && dbt deps && dbt compile && dbt ls && dbt test && dbt build --fail-fast
