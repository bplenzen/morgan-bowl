# Quick Start Guide 🚀

Get your GitLab CI/CD pipeline running in 15 minutes!

## ✅ What's Already Done

You have:
- ✅ Python environment with all dependencies
- ✅ Data for weeks 1-6 ingested
- ✅ DBT models built and tested
- ✅ Automated ingestion script ready
- ✅ GitLab CI/CD pipeline configured

## 🎯 Next Steps (in order)

### Step 1: Initialize Git (2 minutes)

```bash
cd /Users/benlenzen/Codebase/morgan-bowl

# Initialize git repo
git init

# Add files
git add .

# Initial commit
git commit -m "Initial commit: Morgan Bowl data pipeline"
```

### Step 2: Push to GitLab (5 minutes)

1. **Go to [gitlab.com](https://gitlab.com)** and sign in (or create account)

2. **Create new project**:
   - Click "New project" → "Create blank project"
   - Name: `morgan-bowl`
   - Visibility: Private
   - Click "Create project"

3. **Connect your local repo**:
   ```bash
   # Use the URL GitLab shows you (replace YOUR_USERNAME)
   git remote add origin https://gitlab.com/YOUR_USERNAME/morgan-bowl.git
   
   # Push code
   git branch -M main
   git push -u origin main
   ```

### Step 3: Configure Secrets (2 minutes)

In GitLab:
1. Go to **Settings → CI/CD**
2. Expand **Variables**
3. Add these variables:

| Key | Value | Protected | Masked |
|-----|-------|-----------|--------|
| `SLEEPER_LEAGUE_ID` | `1260408876017143808` | ✅ | ✅ |
| `SLEEPER_SEASON` | `2025` | ✅ | ❌ |
| `DUCKDB_PATH` | `data/warehouse.duckdb` | ❌ | ❌ |

### Step 4: Create Schedule (3 minutes)

1. Go to **Build → Pipeline schedules**
2. Click **"New schedule"**
3. Fill in:
   - **Description**: `Weekly fantasy football data ingestion`
   - **Interval Pattern**: `0 6 * * 2` (Every Tuesday at 6 AM)
   - **Timezone**: Select your timezone
   - **Target branch**: `main`
   - **Activated**: ✅
4. Click **"Save"**

### Step 5: Test It! (3 minutes)

1. Go to **Build → Pipelines**
2. Click **"Run pipeline"**
3. Select `main` branch
4. Click **"Run pipeline"**

Watch it run! You should see:
- ✅ Green checkmarks as jobs complete
- Job `ingest:weekly` will show "Nothing to do" (already have week 6)
- Jobs `test:dbt` and `test:python` should pass

## 🎉 Done!

Your pipeline is now scheduled to run **every Tuesday at 6:00 AM**.

### What Happens Next Week (Oct 21)?

On Tuesday morning:
1. GitLab wakes up at 6 AM
2. Runs `weekly_ingestion.py`
3. Script sees week 7 is complete
4. Ingests week 7 data
5. Updates DBT models
6. Runs all tests
7. Stores updated database

You don't have to do anything! ✨

## 🐛 Troubleshooting

### "Pipeline failed - permission denied"
- Check that CI/CD variables are set correctly
- Make sure your GitLab account has permission to run pipelines (free tier = 400 min/month)

### "Can't find database file"
- First run will create database from scratch
- Subsequent runs will download from artifacts

### "Week X already exists"
- This is fine! Script skips weeks that are already ingested

## 📱 Optional: Get Notifications

Set up Slack/email notifications:
1. Go to **Settings → Integrations**
2. Choose Slack or Email
3. Configure webhook/settings
4. Get notified when pipeline completes

## 📚 Learn More

- [Full GitLab Setup Guide](GITLAB_SETUP.md) - Detailed explanations
- [README](README.md) - Project overview and usage
- [GitLab CI/CD Docs](https://docs.gitlab.com/ee/ci/) - Official docs

---

**Questions?** Review the pipeline logs in GitLab under **Build → Pipelines → [click on a run]**
