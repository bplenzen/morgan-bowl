# 🏈 Morgan Bowl Analytics Dashboard

Interactive Streamlit dashboard for exploring fantasy football league data.

## Features

- **📊 Standings**: Current league standings with points for/against
- **🍀 Luck Analysis**: Justice Record showing who's lucky/unlucky
- **📈 Weekly Performance**: Week-by-week scoring and matchup results
- **🔥 Power Rankings**: Combined metric of wins, points, and luck

## Running Locally

```bash
# From project root
poetry run streamlit run analytics/dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Deploying to Streamlit Cloud (FREE!)

1. Push your code to GitLab/GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Set main file path: `analytics/dashboard.py`
5. Deploy!

Your league mates can access it at a public URL like:
`https://[your-app-name].streamlit.app`

## How Justice Record Works

Each week:
- Top 6 scorers get a "justice win" (1-0 for that week)
- Bottom 6 scorers get a "justice loss" (0-1 for that week)

Your **justice record** = what your record *should* be based on scoring performance.

**Luck Differential** = Actual Wins - Justice Wins
- Positive = Lucky (winning more than you deserve)
- Zero = Fair (getting what you deserve)
- Negative = Unlucky (losing more than you deserve)

## Data Source

All data comes from the DuckDB warehouse (`data/warehouse.duckdb`), which is updated weekly via GitLab CI/CD pipeline.
