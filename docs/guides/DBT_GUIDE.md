# DBT Models - Now Live! 🎉

## ✅ What We Just Built

Successfully created a complete DBT transformation pipeline for Morgan Bowl analytics!

### Staging Layer (`main_staging` schema)

Clean, standardized views of raw data:

- ✅ `stg_league` - League metadata
- ✅ `stg_users` - User/manager information
- ✅ `stg_rosters` - Roster assignments
- ✅ `stg_matchups` - All weeks union'd (weeks 1-6 with zero-padding)

### Analytics Layer (`main_analytics` schema)

Business-ready fact tables:

- ✅ `fct_matchups` - Every matchup with opponent info, point differentials, win/loss flags
- ✅ `fct_standings` - Current league standings with wins, losses, points for/against, win%

---

## 🎯 How to Use

### Run All DBT Models

```bash
cd dbt
poetry run dbt run
```

### Run Just Staging

```bash
poetry run dbt run --select staging
```

### Run Just Marts

```bash
poetry run dbt run --select marts
```

### Run Tests

```bash
poetry run dbt test
```

### Query the Results

```bash
# Check standings
poetry run python -c "import duckdb; con = duckdb.connect('data/warehouse.duckdb'); \
con.execute('SELECT * FROM main_analytics.fct_standings ORDER BY wins DESC').show()"

# Check all matchups
poetry run python -c "import duckdb; con = duckdb.connect('data/warehouse.duckdb'); \
con.execute('SELECT * FROM main_analytics.fct_matchups WHERE week = 6').show()"
```

---

## 📊 Data Flow

```
Raw Data (staging schema)
  ├── matchups_week_01..06
  ├── users
  ├── rosters
  └── league
        ↓
Staging Views (main_staging)
  ├── stg_matchups (union all weeks)
  ├── stg_users
  ├── stg_rosters
  └── stg_league
        ↓
Analytics Tables (main_analytics)
  ├── fct_matchups (detailed matchup facts)
  └── fct_standings (aggregated standings)
```

---

## 🔄 Weekly Update Process

When you ingest new data:

```bash
# 1. Ingest latest week
poetry run python -m ingestion.cli --week 7

# 2. Update DBT models (if needed)
# Edit dbt/models/staging/stg_matchups.sql to include week 7
# Update dbt/models/staging/staging_sources.yml to add matchups_week_07

# 3. Rebuild analytics
cd dbt
poetry run dbt run

# 4. Check results
poetry run dbt test
```

---

## 💡 Next Steps

1. **Add more analytics:**
   - Head-to-head records
   - Weekly power rankings
   - Playoff probability
   - Best/worst weeks

2. **Add data quality tests:**
   - Ensure 2 teams per matchup
   - Points are non-negative
   - No missing weeks

3. **Create exposures:**
   - Dashboard definitions
   - Report specifications

4. **Automate:**
   - Schedule weekly ingestion + DBT runs
   - Alert on data quality failures

---

## 📈 Current Standings (via DBT)

| Rank | Manager | Record | Points For | Win % |
|------|---------|--------|------------|-------|
| 1 | jamespancakes | 5-1 | 838.38 | 83.3% |
| 2 | mrbeef1 | 5-1 | 772.80 | 83.3% |
| 3 | MicroMaestros | 4-2 | 766.90 | 66.7% |
| 4 | mrdorsey | 4-2 | 749.70 | 66.7% |
| 5 | AKMCG | 4-2 | 712.26 | 66.7% |
| 6 | jacklamb | 4-2 | 694.16 | 66.7% |
| 7 | georgeuhrick | 3-3 | 626.76 | 50.0% |
| 8 | bplenzen (YOU!) | 2-4 | 735.86 | 33.3% |
| 9 | cariagno | 2-4 | 666.08 | 33.3% |
| 10 | SatoruGojo77 | 2-4 | 652.36 | 33.3% |
| 11 | wsongb | 1-5 | 595.80 | 16.7% |
| 12 | beatlog | 0-6 | 573.62 | 0.0% |

**Note:** You're 8th in standings but 3rd in total points! Classic case of bad luck/scheduling.

---

## 🎓 What You Learned

- ✅ DBT project structure
- ✅ Source definitions
- ✅ Staging vs marts layers
- ✅ Jinja templating in SQL
- ✅ DuckDB adapter configuration
- ✅ Model materialization (views vs tables)

**Your data pipeline is now professional-grade!** 🚀
