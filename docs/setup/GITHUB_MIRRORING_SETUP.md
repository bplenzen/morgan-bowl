# GitHub Mirroring Setup Guide

## Problem Statement

- **Streamlit Cloud** only deploys from GitHub (not GitLab)
- **GitLab CI/CD** runs our data ingestion pipeline
- **Data updates** need to be committed and pushed to both repos
- **Solution**: Auto-commit data updates and mirror everything to GitHub

## Setup Instructions

### Step 1: Create GitLab Project Access Token

The CI/CD pipeline needs permission to push commits back to the GitLab repository.

1. Go to GitLab: <https://gitlab.com/bplenzen/morgan-bowl/-/settings/access_tokens>

2. Click **"Add new token"**

   - **Token name**: `CI/CD Pipeline Push Access`
   - **Expiration date**: Set to 1 year from now (or longer)
   - **Select scopes**:
     - ✅ **write_repository** (REQUIRED - allows pushing commits)
     - ✅ **read_repository** (optional, for completeness)
   - Click **"Create project access token"**

3. **IMPORTANT**: Copy the token immediately! You won't see it again.

4. Go to: <https://gitlab.com/bplenzen/morgan-bowl/-/settings/ci_cd>

5. Expand **"Variables"** section

6. Click **"Add variable"**
   - **Key**: `GITLAB_PUSH_TOKEN`
   - **Value**: Paste the access token you just created
   - **Type**: Variable
   - **Environment scope**: All
   - ✅ **Check "Mask variable"** (CRITICAL!)
   - ❌ **Uncheck "Protect variable"**
   - Click **"Add variable"**

### Step 2: Generate SSH Deploy Key for GitHub

On your local machine, generate a new SSH key specifically for GitLab→GitHub mirroring:

```bash
ssh-keygen -t ed25519 -C "gitlab-ci@morgan-bowl" -f ~/.ssh/gitlab_to_github_mirror
```

**Important**: Leave the passphrase empty (press Enter twice)

### Step 3: Add Public Key to GitHub

1. Copy the **public key**:

   ```bash
   cat ~/.ssh/gitlab_to_github_mirror.pub
   ```

2. Go to GitHub: <https://github.com/bplenzen/morgan-bowl/settings/keys>

3. Click **"Add deploy key"**
   - **Title**: `GitLab CI Mirror`
   - **Key**: Paste the public key
   - ✅ **Check "Allow write access"** (CRITICAL!)
   - Click **"Add key"**

### Step 4: Add Private Key to GitLab

1. Encode the **private key** to base64:

   ```bash
   cat ~/.ssh/gitlab_to_github_mirror | base64 -w 0
   # On macOS, use: cat ~/.ssh/gitlab_to_github_mirror | base64
   ```

2. Copy the entire base64 output (it will be one long line)

3. Go to GitLab: <https://gitlab.com/bplenzen/morgan-bowl/-/settings/ci_cd>

4. Expand **"Variables"**

5. Click **"Add variable"**
   - **Key**: `GITHUB_DEPLOY_KEY`
   - **Value**: Paste the base64-encoded private key
   - **Type**: Variable
   - **Environment scope**: All
   - ✅ **Check "Mask variable"** (CRITICAL!)
   - ❌ **Uncheck "Protect variable"** (unless you only push to protected branches)
   - Click **"Add variable"**

### Step 5: Test the Pipeline

Push a test commit to GitLab:

```bash
git commit --allow-empty -m "test: Verify GitHub mirroring"
git push gitlab main
```

Watch the pipeline at: <https://gitlab.com/bplenzen/morgan-bowl/-/pipelines>

The `mirror:github` job should run and push to GitHub automatically.

### Step 6: Verify Mirroring

Check that the commit appears on GitHub:

```bash
git fetch github
git log github/main -1
```

Should show your latest commit.

## How It Works

### For Code Changes

1. You push code to GitLab: `git push`
2. GitLab CI/CD runs the `mirror:github` job
3. The job uses the SSH deploy key to push to GitHub
4. GitHub receives the update
5. Streamlit Cloud detects the GitHub push and auto-deploys

### For Scheduled Data Ingestion

1. GitLab scheduled pipeline runs weekly
2. `ingest:weekly` job fetches data from Sleeper API and updates `data/warehouse.duckdb`
3. `test:dbt` and `test:api_parity` jobs validate the data
4. `commit:data` job commits the updated database with timestamp
5. `mirror:github` job pushes everything to GitHub
6. Streamlit Cloud deploys with fresh data
7. **Fully automated - no manual intervention needed!**

## Workflow After Setup

```bash
# Standard workflow (only push to GitLab):
git add .
git commit -m "Your changes"
git push  # This goes to GitLab (origin)

# GitLab CI/CD automatically mirrors to GitHub
# Streamlit Cloud automatically deploys from GitHub
# 🎉 Everything happens automatically!
```

## Troubleshooting

### Mirror job fails with "Permission denied"

- Verify the deploy key has **write access** enabled on GitHub
- Verify the `GITHUB_DEPLOY_KEY` variable is set correctly in GitLab
- Check that the private key was base64-encoded correctly

### Mirror job fails with "unknown host"

- The `ssh-keyscan github.com` step may have failed
- Check GitLab CI/CD logs for network issues

### Commits not appearing on GitHub

- Check the GitLab pipeline: <https://gitlab.com/bplenzen/morgan-bowl/-/pipelines>
- Look at the `mirror:github` job logs
- Verify the job ran successfully (not skipped due to rules)

### Streamlit not deploying

- Streamlit Cloud may take 2-5 minutes to detect changes
- Check Streamlit Cloud logs: <https://share.streamlit.io/>
- Verify the GitHub repo is connected to Streamlit Cloud

## Security Notes

- The private key is base64-encoded (not for security, just for storage)
- The key is **masked** in GitLab CI/CD logs
- The key only has access to **one repository** (morgan-bowl)
- The key is **write-only** for GitHub (can't read private data)
- If compromised, simply delete the deploy key from GitHub and regenerate

## Cleanup (if needed)

To remove the mirroring:

1. Delete the deploy key from GitHub: <https://github.com/bplenzen/morgan-bowl/settings/keys>
2. Delete the `GITHUB_DEPLOY_KEY` variable from GitLab: <https://gitlab.com/bplenzen/morgan-bowl/-/settings/ci_cd>
3. Delete the `mirror:github` job from `.gitlab-ci.yml`
4. Delete the local SSH key: `rm ~/.ssh/gitlab_to_github_mirror*`
