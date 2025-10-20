# Configuration Guide

Advanced configuration options for Morgan Bowl.

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [DBT Configuration](#dbt-configuration)
3. [GitLab CI/CD Setup](#gitlab-cicd-setup)
4. [Streamlit Secrets](#streamlit-secrets)
5. [League-Specific Settings](#league-specific-settings)

---

## Environment Variables

Create a `.env` file in the project root:

```bash
# Required
SLEEPER_LEAGUE_ID=1260408876017143808  # Your Sleeper league ID
SLEEPER_SEASON=2025                     # Current season year

# Optional
DUCKDB_PATH=data/warehouse.duckdb       # Database location
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
```

### Finding Your League ID

1. Go to [sleeper.com](https://sleeper.com)
2. Navigate to your league
3. Check the URL: `https://sleeper.com/leagues/YOUR_LEAGUE_ID`
4. Copy the long number

---

## DBT Configuration

### Local Development

1. **Copy example profile**:

   ```bash
   cp dbt/profiles.example.yml ~/.dbt/profiles.yml
   ```

2. **Edit `~/.dbt/profiles.yml`**:

   ```yaml
   morgan_bowl:
     outputs:
       dev:
         type: duckdb
         path: /absolute/path/to/morgan-bowl/data/warehouse.duckdb
         schema: main_analytics
         threads: 4
     target: dev
   ```

3. **Test connection**:

   ```bash
   cd dbt
   poetry run dbt debug
   ```

### CI/CD Environment

GitLab CI uses environment variables (no `~/.dbt/profiles.yml` needed):

```yaml
# .gitlab-ci.yml (already configured)
variables:
  DBT_PROFILES_DIR: ./dbt
  DUCKDB_PATH: data/warehouse.duckdb
```

---

## GitLab CI/CD Setup

### Initial Setup

1. **Push code to GitLab**:

   ```bash
   git remote add origin https://gitlab.com/YOUR_USERNAME/morgan-bowl.git
   git push -u origin main
   ```

2. **Configure CI/CD Variables** (Settings → CI/CD → Variables):

   | Key | Value | Protected | Masked |
   |-----|-------|-----------|--------|
   | `SLEEPER_LEAGUE_ID` | Your league ID | ✅ | ✅ |
   | `SLEEPER_SEASON` | `2025` | ✅ | ❌ |
   | `DUCKDB_PATH` | `data/warehouse.duckdb` | ❌ | ❌ |

3. **Create Pipeline Schedule** (Build → Pipeline Schedules):
   - **Description**: Weekly fantasy football data ingestion
   - **Interval Pattern**: `0 6 * * 2` (Tuesday 6 AM)
   - **Timezone**: Your timezone
   - **Target Branch**: `main`
   - **Activated**: ✅

### Pipeline Stages

```yaml
stages:
  - ingest   # Pull data from Sleeper API
  - build    # Run DBT transformations
  - test     # Execute tests
```

### Manual Pipeline Triggers

Run pipeline manually: Build → Pipelines → Run Pipeline

---

## Streamlit Secrets

### Local Development

Create `.streamlit/secrets.toml`:

```toml
# Database connection
duckdb_path = "../data/warehouse.duckdb"

# Optional: Email notifications
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "your-email@gmail.com"
sender_password = "your-app-password"

# Optional: Slack notifications
[slack]
webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Streamlit Cloud Deployment

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your repository
3. Set **main file path**: `analytics/dashboard.py`
4. Add secrets (Settings → Secrets):

   ```toml
   duckdb_path = "data/warehouse.duckdb"
   ```

5. Deploy!

---

## League-Specific Settings

### Auto-Detected Settings

Morgan Bowl automatically detects:

- ✅ Total teams (8, 10, 12, 14+)
- ✅ Playoff teams (4, 6, 8)
- ✅ Playoff week start
- ✅ Scoring format (PPR, Half-PPR, Standard)
- ✅ Roster positions

### Manual Overrides (Optional)

Edit `dbt/dbt_project.yml` to override auto-detection:

```yaml
vars:
  league_size: 12              # Total teams
  playoff_teams: 6             # Teams making playoffs
  playoff_week_start: 15       # Week playoffs begin
  current_season: 2025         # Season year
```

**Note**: Models use `COALESCE(auto_detected_value, manual_override)`, so auto-detection takes precedence.

### Validation

Check if your configuration matches Sleeper API:

```bash
poetry run python -m ingestion.cli
# Look for "Configuration Validation" in output
```

---

## Advanced: Custom DBT Variables

### Add New Variables

1. **Edit `dbt/dbt_project.yml`**:

   ```yaml
   vars:
     my_custom_var: "value"
   ```

2. **Use in SQL models**:

   ```sql
   SELECT {{ var('my_custom_var') }} AS custom_value
   ```

3. **Override at runtime**:

   ```bash
   dbt run --vars '{"my_custom_var": "new_value"}'
   ```

---

## Troubleshooting

### DBT Connection Issues

```bash
# Test connection
cd dbt
poetry run dbt debug

# Common fix: Wrong database path
# Edit ~/.dbt/profiles.yml with absolute path
```

### CI/CD Pipeline Failures

**Check GitLab CI/CD logs**: Build → Pipelines → Click failed job

Common issues:

1. **Missing variables**: Add to Settings → CI/CD → Variables
2. **Wrong timezone**: Edit pipeline schedule
3. **Database locked**: Ensure no local processes accessing DuckDB

### Dashboard Not Loading Data

**Check database path** in `.streamlit/secrets.toml`:

```toml
# Use relative path from analytics/ directory
duckdb_path = "../data/warehouse.duckdb"
```

**Test database connection**:

```python
import duckdb
conn = duckdb.connect('data/warehouse.duckdb', read_only=True)
conn.execute("SELECT * FROM main_analytics.fct_standings").show()
```

---

## Security Best Practices

### ✅ DO

- Use environment variables for secrets (`.env` file)
- Add `.env` to `.gitignore` (already done)
- Use GitLab CI/CD masked variables
- Use read-only database connections in dashboard
- Enable 2FA on Sleeper account

### ❌ DON'T

- Commit `.env` file to git
- Hardcode API keys in code
- Use admin database connections in public dashboards
- Share your league ID publicly (if league is private)

---

## Optional: Email/Slack Notifications

### Email Setup

1. **Create app password** (Gmail example):
   - Go to Google Account → Security → 2-Step Verification
   - App passwords → Generate new password

2. **Add to `.streamlit/secrets.toml`**:

   ```toml
   [email]
   smtp_server = "smtp.gmail.com"
   smtp_port = 587
   sender_email = "your-email@gmail.com"
   sender_password = "your-app-password"
   recipient_emails = ["league-mate-1@example.com", "league-mate-2@example.com"]
   ```

3. **Update report script**:

   ```python
   # scripts/generate_report.py (modify send_report function)
   ```

### Slack Setup

1. **Create Slack webhook**:
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Create new app → Incoming Webhooks
   - Copy webhook URL

2. **Add to `.streamlit/secrets.toml`**:

   ```toml
   [slack]
   webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

---

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/bplenzen/morgan-bowl/issues)
- **Docs**: Check README and CHANGELOG
- **DBT Docs**: `cd dbt && poetry run dbt docs generate && dbt docs serve`
