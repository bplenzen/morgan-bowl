---

### `.github/ISSUE_TEMPLATE/dbt-model-addition.md`

```md
---
name: dbt Model Addition / Change
about: Track new or modified dbt models with tests and docs
labels: dbt
---

## Model(s)

- Name(s):
- Folder: staging / intermediate / marts

## Purpose

- Business logic and downstream consumers (exposures):

## Inputs & Contracts

- Sources/refs:
- Column contracts (name:type:nullable:unique):

## Tests (schema.yml)

- [ ] `not_null` on key columns
- [ ] `unique` on primary/business keys
- [ ] `relationships` for FKs
- [ ] Additional tests (accepted_values, custom)

## Freshness & Performance

- [ ] Source freshness (if applicable)
- [ ] Expected size & latency
- [ ] Index/partition/sort (DuckDB ops/PRAGMA noted)

## Docs

- [ ] Model description written
- [ ] Columns documented

## Validation

```bash
cd dbt_morgan_bowl
dbt deps && dbt compile
dbt run -s <model> && dbt test -s <model>
dbt build --fail-fast -s <model>
