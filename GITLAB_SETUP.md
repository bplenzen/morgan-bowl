# GitLab CI/CD Setup Guide

This guide walks you through setting up automated weekly data ingestion using GitLab CI/CD.

## 📋 Prerequisites

- GitLab account (free tier is fine)
- Git installed locally
- Your code ready to push

## 🚀 Step 1: Initialize Git Repository

```bash
cd /Users/benlenzen/Codebase/morgan-bowl

# Initialize git if not already done
git init

# Add all files
git add .

# Make initial commit
git commit -m "Initial commit: Morgan Bowl data pipeline"
```

## 📦 Step 2: Create GitLab Repository

1. Go to [GitLab.com](https://gitlab.com)
2. Sign in (or create account)
3. Click **"New project"**
4. Choose **"Create blank project"**
5. Name it: `morgan-bowl`
6. Visibility: **Private** (recommended)
7. Click **"Create project"**

## 🔗 Step 3: Connect Local Repo to GitLab

GitLab will show you commands like these (use YOUR URL):

```bash
# Add GitLab as remote
git remote add origin git@gitlab.com:YOUR_USERNAME/morgan-bowl.git

# Or if using HTTPS:
# git remote add origin https://gitlab.com/YOUR_USERNAME/morgan-bowl.git

# Push your code
git branch -M main
git push -u origin main
```

## 🔐 Step 4: Configure CI/CD Variables

Your pipeline needs access to your Sleeper league ID. Set it up as a **secret variable**:

1. In GitLab, go to your project
2. Navigate to **Settings → CI/CD**
3. Expand **Variables** section
4. Click **"Add variable"**
5. Add these variables:

| Key | Value | Flags |
|-----|-------|-------|
| `SLEEPER_LEAGUE_ID` | `1260408876017143808` | Protected: ✅, Masked: ✅ |
| `SLEEPER_SEASON` | `2025` | Protected: ✅ |
| `DUCKDB_PATH` | `data/warehouse.duckdb` | - |

## ⏰ Step 5: Create Scheduled Pipeline

Set up the pipeline to run every Tuesday at 6:00 AM:

1. In GitLab, go to **Build → Pipeline schedules**
2. Click **"New schedule"**
3. Fill in:
   - **Description**: `Weekly fantasy football data ingestion`
   - **Interval Pattern**: Custom (`0 6 * * 2`)
     - This is cron format: "At 06:00 on Tuesday"
   - **Cron timezone**: Select your timezone (e.g., `America/New_York`)
   - **Target branch**: `main`
   - **Activated**: ✅ Check this box
4. Click **"Save pipeline schedule"**

### Understanding Cron Syntax
```
 ┌───────────── minute (0 - 59)
 │ ┌───────────── hour (0 - 23)
 │ │ ┌───────────── day of month (1 - 31)
 │ │ │ ┌───────────── month (1 - 12)
 │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
 │ │ │ │ │
 0 6 * * 2
```
- `0` = minute 0 (top of the hour)
- `6` = 6 AM
- `*` = every day of month
- `*` = every month  
- `2` = Tuesday (0=Sunday, 1=Monday, 2=Tuesday, etc.)

## 🧪 Step 6: Test the Pipeline

Before waiting for the schedule, test it manually:

1. Go to **Build → Pipelines**
2. Click **"Run pipeline"**
3. Select branch: `main`
4. Click **"Run pipeline"**

Watch it run! You should see:
- ✅ `ingest:weekly` - Data ingestion
- ✅ `test:dbt` - DBT tests
- ✅ `test:python` - Python tests

## 📊 Step 7: Handle Database Artifacts

**Challenge**: Your DuckDB file grows each week. GitLab has two options:

### Option A: Use Artifacts (Simple)
- The `.gitlab-ci.yml` already stores `warehouse.duckdb` as an artifact
- Downloads it at the start of each run
- **Limitation**: Artifacts expire (default 7 days)

### Option B: Use Git LFS (Better for long-term)
```bash
# Install Git LFS
brew install git-lfs
git lfs install

# Track the database file
git lfs track "data/*.duckdb"
git add .gitattributes
git commit -m "Track DuckDB with Git LFS"
git push
```

### Option C: Use External Storage (Most Enterprise)
- Store DuckDB in S3, Google Cloud Storage, or GitLab's package registry
- Not necessary for your use case, but good to know

**Recommendation**: Start with Option A (artifacts), upgrade to Option B if needed.

## 🔔 Step 8: Set Up Notifications (Optional)

Get notified when ingestion completes:

1. Go to **Settings → Integrations**
2. Choose integration:
   - **Slack**: Get pipeline results in Slack
   - **Email**: Configure email notifications
   - **Discord/Teams**: Also available

## 🎯 What Happens Now?

Every **Tuesday at 6:00 AM**:
1. GitLab runner starts
2. Checks current NFL week
3. Ingests any missing weeks
4. Runs DBT to update analytics
5. Runs tests to validate data
6. Stores database as artifact
7. (Optional) Sends you notification

## 🐛 Troubleshooting

### Pipeline fails with "No such file: .env"
- The `.env` file is gitignored (good for security)
- Use CI/CD variables instead (Step 4)

### "poetry: command not found"
- The pipeline installs Poetry automatically
- If it fails, check the `before_script` in `.gitlab-ci.yml`

### Database file too large
- Upgrade to Git LFS (Option B above)
- Or exclude from git entirely and use external storage

### Wrong timezone
- Update the schedule's timezone setting
- GitLab uses UTC by default

## 📚 Next Steps

- **Monitor runs**: Check **Build → Pipelines** each Tuesday
- **Add notifications**: Set up Slack/email alerts
- **Expand pipeline**: Add data quality checks, visualizations, etc.
- **Learn more**: [GitLab CI/CD docs](https://docs.gitlab.com/ee/ci/)

## 🎓 What You're Learning (Enterprise Skills)

- ✅ **CI/CD pipelines** (YAML configuration)
- ✅ **Scheduled jobs** (like Control-M at your company)
- ✅ **Secrets management** (environment variables)
- ✅ **Artifact storage** (build outputs)
- ✅ **Pipeline stages** (ingest → build → test)
- ✅ **Infrastructure as Code** (everything in git)

---

**Questions?** Check the troubleshooting section or review the pipeline logs in GitLab!
