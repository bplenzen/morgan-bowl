# Morgan Bowl Feature Roadmap

## 🎯 Version 1.0.1 - Critical Fixes (NEXT RELEASE)

### 🔴 Critical Priority (Must Fix Before Sharing Widely)

1. **Add Error Handling to Dashboard** ([`analytics/dashboard.py`](../analytics/dashboard.py))
   - Current Issue: Dashboard crashes when database queries fail
   - Fix: Add try-except blocks, show user-friendly error messages
   - Impact: Prevents embarrassing crashes when league mates use it
   - Effort: 1 hour

2. **Fix SQL Injection Vulnerability in Report Generator** ([`scripts/generate_report.py`](../scripts/generate_report.py))
   - Current Issue: Uses f-strings for SQL queries (security risk)
   - Fix: Use parameterized queries
   - Impact: Security vulnerability
   - Effort: 30 minutes

### 🟡 High Priority (Should Fix Soon)

3. **Parameterize Hardcoded League Size** ([`dbt/models/marts/fct_justice_record.sql`](../dbt/models/marts/fct_justice_record.sql))
   - Current Issue: League size hardcoded as `6` in justice record calculation
   - Fix: Move to `dbt_project.yml` config variable
   - Impact: Makes code reusable for different league sizes
   - Effort: 2 hours

4. **Fix Hardcoded Season Year** ([`src/ingestion/pipeline.py`](../src/ingestion/pipeline.py))
   - Current Issue: Year defaults to `2025`, doesn't auto-detect
   - Fix: Extract year from Sleeper API response
   - Impact: Prevents manual updates every season
   - Effort: 15 minutes

5. **Fix Markdown Linting Issues** (260 warnings across docs)
   - Current Issue: Inconsistent markdown formatting
   - Fix: Run `markdownlint-cli2` and clean up warnings
   - Impact: Professional documentation appearance
   - Effort: 30 minutes

---

## 🚀 Version 1.1.0 - Advanced Analytics (Q4 2024)

### Player Analytics & Insights

6. **Playoff Probability Simulator** 🎲
   - Monte Carlo simulation for playoff chances
   - New model: `dbt/models/marts/fct_playoff_probability.sql`
   - Simulate remaining games 10,000 times
   - Calculate % chance each team makes playoffs
   - Impact: HIGH - League mates love seeing their playoff odds
   - Complexity: Medium (3-4 hours)

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

1. ✅ Version 1.0.0 - COMPLETED
2. 🔴 Critical fixes (#1-2)
3. 📧 Enable notifications (#12) - High impact, low effort!

### Short Term (Next 2-4 Weeks)

4. 🟡 High priority fixes (#3-5)
5. 🚑 **Injury Impact Analysis (#8)** - NEW! League mates will love this
6. 📊 **Draft Performance Analysis (#9)** - NEW! Great for roasting bad picks
7. 🎲 Playoff simulator (#6) - Most exciting feature
8. 📊 Strength of schedule (#7) - Easy win

### Medium Term (Next Quarter)

9. 🏈 Player analytics (#10)
10. 🔐 Security hardening (#13-15)
11. 📈 Monitoring setup (#16-18)

### Long Term (6+ Months)

12. 📊 DBT semantic layer (#19)
13. 🌐 Multi-league support (#23)
14. 🤖 ML predictions (#25)

---

## 📊 Impact vs. Effort Matrix

### Quick Wins (High Impact, Low Effort)

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
**Current Version**: 1.0.0
**Next Release**: 1.0.1 (Critical Fixes)
**Target for 2.0.0**: ~2 weeks (after 1.0.1 is solid)

**Development Philosophy**:

- **Quality over speed** - Take time to learn DataOps patterns correctly
- **Test-driven** - Write tests for all fixes and features
- **Document everything** - Before/after examples, learning notes
- **One thing at a time** - Master each concept before moving on

**🔥 NEW FEATURES ADDED** (Planned for 2.0.0):

- **Injury Impact Analysis** - Quantify how unlucky each team has been with injuries
- **Draft Performance Analysis** - Compare draft picks to current player rankings

**Release Strategy**:

- **v1.0.1** (This week): Critical fixes, learn defensive programming
- **v1.1.0** (Week 2-3): Quick wins (notifications, strength of schedule)
- **v2.0.0** (~2 weeks): New features (injury + draft analysis)

**Quick Win Alert**: Feature #12 (Email/Slack notifications) is already coded! Just needs environment variables set up. This is the highest ROI feature available right now.
