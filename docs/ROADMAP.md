# Morgan Bowl Feature Roadmap

## ✅ Version 1.0.1 - Critical Fixes (RELEASED 2025-10-19)

**All items completed! See [RELEASE_1.0.1.md](releases/RELEASE_1.0.1.md) for details.**

- ✅ Add Error Handling to Dashboard
- ✅ Fix SQL Injection Vulnerability in Report Generator
- ✅ Parameterize Hardcoded League Size
- ✅ Fix Hardcoded Season Year
- ✅ Configure Pre-commit Hooks (Black, isort, Ruff, SQLFluff)

**Note:** Markdown linting warnings (260+) are cosmetic and will be addressed in v2.0.0 documentation refactor.

---

## 🚀 Version 1.1.0 - Advanced Analytics (NEXT RELEASE)

### Configuration & Portability

**1. Universal League Configuration** 🌍 **[HIGH PRIORITY]**
   - **Goal**: Make Morgan Bowl work for ANY Sleeper league with just a league ID
   - **Current State**: Already has `SLEEPER_LEAGUE_ID` env var, league_size/playoff_teams in DBT vars
   - **Needed Changes**:
     - Create comprehensive `league_config.yml` for league-specific settings
     - Add validation to ensure config matches actual league (12 teams = 12 teams)
     - Auto-detect league settings from Sleeper API where possible:
       - Total teams (roster count)
       - Playoff teams (from league settings)
       - Scoring type (PPR, Half-PPR, Standard)
       - Regular season weeks (from league settings)
     - Update README with "Quick Start: Any League" instructions
   - **Files to modify**:
     - `src/ingestion/config.py` - Expand config class
     - `src/ingestion/pipeline.py` - Fetch league settings from API
     - `dbt/dbt_project.yml` - Auto-populate vars from ingested data
     - `README.md` - Add "Use in Your League" section
   - **Future Enhancement**: ESPN & Yahoo league import (v2.0+)
   - **Impact**: VERY HIGH - Makes project usable by anyone
   - **Complexity**: Medium (4-6 hours)
   - **Effort**: One-time setup, huge reusability benefit

### Player Analytics & Insights

6. **Strength of Schedule Analysis** 📊

7. **Strength of Schedule Analysis** 📊
   - Track opponent difficulty over time
   - New model: `dbt/models/marts/fct_strength_of_schedule.sql`
   - Calculate average opponent win%
   - Show remaining opponent strength
   - Impact: Medium - Explains why some teams have harder schedules
   - Complexity: Low (2 hours)

8. **Injury Impact & Bad Luck Analysis** 🚑 **[NEW - HIGH PRIORITY]**
   - Quantify how injuries have affected each team
   - New models:
     - `dbt/models/staging/stg_player_injuries.sql` - Player injury data from Sleeper
     - `dbt/models/marts/fct_injury_impact.sql` - Games missed, points lost per team
     - `dbt/models/marts/fct_bad_luck_rankings.sql` - "Unluckiest Team" rankings
   - Metrics tracked:
     - **Games Missed**: Total games lost to injury per team
     - **Points Missed**: Projected points lost (based on player's season avg)
     - **Draft Capital Lost**: ADP/draft position of injured players
     - **Injury Severity Score**: Weighted by player quality + games missed
     - **Bad Luck Index**: Composite score ranking teams by injury misfortune
   - Data sources:
     - Sleeper API: Player injury status (IR, Out, Doubtful)
     - Player stats: Season averages for projection
     - Draft data: Original draft position/ADP
   - Impact: **VERY HIGH** - Everyone wants to complain about injuries!
   - Complexity: Medium-High (6-8 hours)
     - Requires new Sleeper API endpoints for injury data
     - Math for projecting "lost points" is non-trivial
     - Need historical player performance data

9. **Draft Performance Analysis** 📊 **[NEW - HIGH PRIORITY]**
   - Compare draft picks to current player rankings
   - New models:
     - `dbt/models/staging/stg_draft_picks.sql` - Draft results from Sleeper
     - `dbt/models/staging/stg_player_rankings.sql` - Current season rankings
     - `dbt/models/marts/fct_draft_analysis.sql` - Draft pick value analysis
   - Metrics calculated:
     - **Draft Position vs. Current Rank**: "Ja'Marr Chase: Drafted 1.01, Currently WR10/Overall 20"
     - **Pick Value Score**: How much better/worse than draft slot
     - **Positional Accuracy**: Did you draft WR1 or WR10?
     - **Hits & Busts**: Players outperforming/underperforming by >10 spots
     - **Draft Grade by Manager**: Overall draft performance score
     - **Best/Worst Pick**: Biggest steal and biggest bust per team
     - **Round Analysis**: Which rounds did you hit/miss on?
   - Visualizations:
     - Draft board heatmap (red = bust, green = hit)
     - Scatter plot: Draft position vs. Current rank
     - Manager draft grade report card
   - Impact: **VERY HIGH** - Draft analysis is endlessly entertaining
   - Complexity: Medium (5-6 hours)
     - Need draft data from Sleeper API
     - Need current player rankings (external API like FantasyPros?)
     - Math for "value over replacement" calculations

10. **Player-Level Analytics** 🏈
    - Track individual player performance across rosters
    - New staging: `dbt/models/staging/stg_player_stats.sql`
    - Track player points, starts, benchings
    - Identify best/worst draft picks
    - Impact: HIGH - Most requested feature
    - Complexity: High (8-10 hours, requires new API endpoints)

11. **Trade Analyzer** 🤝
    - Evaluate trade fairness using historical data
    - New feature: `analytics/trade_analyzer.py`
    - Input: proposed trade details
    - Output: value analysis, historical performance comparison
    - Impact: Medium - Fun but not critical
    - Complexity: Medium (4-5 hours)

### Notifications & Automation

10. **Weekly Email/Slack Notifications** 📧
    - **Status**: Already implemented in `scripts/generate_report.py`!
    - Just needs environment variables configured:

      ```bash
      export EMAIL_SENDER="your-email@gmail.com"
      export EMAIL_PASSWORD="your-app-password"
      # OR
      export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
      ```

    - Impact: HIGH - Automatic engagement, no manual sharing needed
    - Complexity: LOW (30 minutes - just configuration)

---

## 🔐 Version 1.2.0 - Security & Infrastructure (Q1 2025)

### Security Hardening

11. **Dependency Vulnerability Scanning**
    - Add `safety` to GitLab CI pipeline
    - Automated security checks on every commit
    - Alert on known vulnerabilities
    - Effort: 1 hour

12. **Secret Scanning Pre-Commit Hook**
    - Add `detect-secrets` to pre-commit
    - Prevent accidental secret commits
    - Create `.secrets.baseline` file
    - Effort: 30 minutes

13. **Database Backup Strategy**
    - Weekly backups to S3/Google Cloud Storage
    - Incremental backups with retention policy
    - Automated backup script in GitLab schedule
    - Effort: 3-4 hours

### Monitoring & Observability

14. **Error Tracking with Sentry**
    - Add Sentry integration for runtime error tracking
    - Get alerts when dashboard crashes
    - Track error frequency and patterns
    - Effort: 2 hours

15. **Pipeline Failure Notifications**
    - GitLab pipeline failure emails/Slack alerts
    - Data freshness monitoring
    - Alert if pipeline is >1 week behind
    - Effort: 1 hour

16. **Data Freshness Monitoring**
    - Alert if last ingestion was >7 days ago
    - Automatic staleness detection in dashboard
    - "Last updated: X days ago" warning banner
    - Effort: 2 hours

---

## 📈 Version 2.0.0 - Platform Expansion (Q2 2025)

### 📚 Documentation Consolidation

**MAJOR CLEANUP:** Consolidate 23 markdown files → 3 essential docs

**Rationale:** Wait until v2.0.0 to avoid redoing work as features are added in v1.x releases.

**Target Structure:**

1. **`README.md`** (root) - User-facing quick start
   - What is Morgan Bowl?
   - 5-minute setup guide
   - How to use the dashboard
   - Feature highlights (Justice Record, Injury Analysis, Draft Analysis, etc.)
   - Screenshots and examples

2. **`DEVELOPMENT.md`** (root) - Developer/contributor documentation
   - Architecture overview & tech stack
   - Detailed development setup
   - DBT guide and model documentation
   - Testing strategy
   - CI/CD pipeline explanation
   - Release process
   - Roadmap (current + future)

3. **`CHANGELOG.md`** (root) - Version history
   - Keep standard changelog format
   - Include release notes inline (not separate files)
   - Links to detailed feature specs if needed

**Archive to `docs/archive/`:**

- Old release notes (RELEASE_1.0.0.md, RELEASE_1.0.1.md, etc.)
- Draft feature specs (FEATURE_SPEC_*.md)
- Learning logs (nice reference material)
- Old reviews (CODE_REVIEW.md, TECH_REVIEW_*.md)

**Delete:**

- Duplicate/outdated setup guides
- Internal planning docs (.organization-summary.md, NEXT_STEPS.md)

**Impact:** Clean, professional first impression. New contributors/users find what they need immediately.

**Effort:** 4-6 hours (careful merging of content, updating references)

---

### Data Quality & Consistency

17. **DBT Semantic Layer**
    - Define reusable metrics (win%, points per game, etc.)
    - Prevent calculation duplication across models
    - Single source of truth for metric definitions
    - Effort: 4-6 hours

18. **Historical Data Consistency Tests**
    - Ensure past weeks' data never changes
    - Checksum verification for completed weeks
    - Alert if historical data is modified
    - Effort: 3 hours

19. **Advanced DBT Testing**
    - Custom data quality tests (outlier detection)
    - Cross-model relationship tests
    - Data distribution tests (e.g., scores should be 80-200)
    - Effort: 4 hours

### Performance & Scalability

20. **Query Performance Optimization**
    - Create denormalized dashboard summary view
    - Add database indexes for common queries
    - Implement query result caching
    - Effort: 3-4 hours

21. **Multi-League Support**
    - Parameterize league configuration
    - Support multiple fantasy leagues in one database
    - League selector in dashboard
    - Effort: 8-10 hours (major feature)

22. **Mobile-Responsive Dashboard**
    - Optimize Streamlit dashboard for mobile
    - Responsive layouts for phone screens
    - Touch-friendly controls
    - Effort: 4-5 hours

---

## 🎨 Version 3.0.0 - Premium Features (Future)

### Advanced Analytics

23. **Machine Learning Predictions**
    - Predict weekly matchup outcomes
    - Player performance forecasting
    - Draft pick value predictions
    - Effort: 20+ hours (research + implementation)

24. **Custom Scoring Systems**
    - Support different league scoring rules
    - What-if analysis for scoring changes
    - Historical re-scoring with different rules
    - Effort: 6-8 hours

25. **Waiver Wire Recommendations**
    - Analyze available players
    - Recommend pickups based on team needs
    - Projected impact analysis
    - Effort: 10-12 hours

### Social Features

26. **League Chat Integration**
    - Display Sleeper league chat messages
    - Sentiment analysis on trash talk
    - "Most active trash talker" award
    - Effort: 6-8 hours

27. **Historical Season Comparison**
    - Multi-season database
    - Year-over-year performance tracking
    - Dynasty league support
    - Effort: 8-10 hours

---

## 🏆 Recommended Priority Order

### Immediate (This Week)

1. ✅ Version 1.0.1 - COMPLETED (Oct 19, 2025)
2. 🌍 **Universal League Configuration (#1)** - Make it work for ANY league!
3. 📊 **Strength of Schedule (#6)** - Easy analytics win

### Short Term (Next 2-4 Weeks) - v1.1.0

4.  **Injury Impact Analysis (#8)** - League mates will love this
5. 📊 **Draft Performance Analysis (#9)** - Great for roasting bad picks
6. 📧 Enable notifications (#10) - Already coded, just needs env vars!

### Deferred Features

- 🎲 **Playoff Probability Simulator** - Postponed (complex, less immediate value)
  - Will revisit in v1.2.0 or v2.0.0
  - Focus on league portability and core analytics first

### Medium Term (Next Quarter)

7. 🏈 Player analytics (#11)
8. 🔐 Security hardening
9. 📈 Monitoring setup

### Long Term (6+ Months) - v2.0.0

10. � Documentation consolidation (23 files → 3)
11. 🌐 ESPN/Yahoo league import
12. 📊 DBT semantic layer
13. 🤖 ML predictions

---

## 📊 Impact vs. Effort Matrix

### Quick Wins (High Impact, Low Effort)

- 🌍 **Universal League Config (#1)** - 4-6 hours - **DO THIS FIRST!**
- 📧 Email/Slack notifications (#10) - 30 min (already coded!)
- 📊 Strength of schedule (#6) - 2 hours

- 📧 Email/Slack notifications (#12) - 30 min
- 🟡 Fix hardcoded year (#4) - 15 min
- 🟡 Markdown linting (#5) - 30 min
- 📊 Strength of schedule (#7) - 2 hours

### Major Projects (High Impact, High Effort) ⭐ **NEW FEATURES**

- 🚑 **Injury Impact & Bad Luck Rankings (#8)** - 6-8 hours - **DO THIS FIRST!**
- 📊 **Draft Performance Analysis (#9)** - 5-6 hours - **DO THIS SECOND!**
- 🎲 Playoff simulator (#6) - 3-4 hours
- 🏈 Player analytics (#10) - 8-10 hours
- 🌐 Multi-league support (#23) - 8-10 hours

### Fill Projects (Low Impact, Low Effort)

- 🔐 Secret scanning (#14) - 30 min
- 📈 Data freshness alerts (#18) - 2 hours

### Thankless Tasks (Low Impact, High Effort)

- 🤖 ML predictions (#25) - 20+ hours (save for later)

---

## 📝 Notes

**Last Updated**: October 19, 2025
**Current Version**: 1.0.1 ✅
**Next Release**: 1.1.0 (Advanced Analytics)
**Target for 2.0.0**: Q2 2025 (after feature set matures)

**Development Philosophy**:

- **Quality over speed** - Take time to learn DataOps patterns correctly
- **Test-driven** - Write tests for all fixes and features
- **Document everything** - Before/after examples, learning notes
- **One thing at a time** - Master each concept before moving on
- **Wait to refactor docs** - Let features stabilize before v2.0.0 doc consolidation

**🔥 PRIORITY FEATURES** for v1.1.0:

1. **Universal League Configuration** - Make Morgan Bowl work for ANY Sleeper league
2. **Strength of Schedule** - Easy analytics win, useful insights
3. **Injury Impact Analysis** - Quantify how unlucky each team has been with injuries
4. **Draft Performance Analysis** - Compare draft picks to current player rankings, roast bad picks!

**⏸️ DEFERRED FEATURES**:

- **Playoff Probability Simulator** - Postponed to v1.2.0 or later
  - Reason: Complex implementation, less immediate value than league portability
  - Focus: Build foundation for universal league support first

**📚 DOCUMENTATION STRATEGY**:

- **v1.x releases**: Keep adding to existing docs as needed (don't worry about duplication)
- **v2.0.0**: Major documentation consolidation (23 files → 3 essential docs)
- **Rationale**: Avoid redoing documentation work as features evolve

**🌐 LONG-TERM VISION**:

- **v2.0.0**: ESPN & Yahoo league import (unified fantasy platform analytics)
- **Platform-agnostic**: Work with any fantasy football league, any platform

**Release Strategy**:

- ✅ **v1.0.1** (Oct 19, 2025): Critical security & quality fixes - SHIPPED!
- 🎯 **v1.1.0** (Next): Advanced analytics (injury impact, draft analysis, playoff simulator)
- 📈 **v2.0.0** (Q2 2025): Documentation consolidation + platform expansion features

**Quick Win Alert**: Feature #12 (Email/Slack notifications) is already coded! Just needs environment variables set up. This is the highest ROI feature available right now.
