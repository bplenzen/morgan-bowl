"""
Weekly Report Generator
Generates a markdown report of the week's results and sends it via email or posts to Slack.
"""

import duckdb
from pathlib import Path
from datetime import datetime
import os


def generate_weekly_report(week: int) -> str:
    """Generate a markdown report for a specific week"""
    
    db_path = Path(__file__).parent.parent / "data" / "warehouse.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    
    # Get current date
    report_date = datetime.now().strftime("%B %d, %Y")
    
    # Get weekly matchup results
    matchups = conn.execute(f"""
        SELECT 
            manager_name,
            round(points, 2) as points,
            opponent_manager_name,
            round(opponent_points, 2) as opponent_points,
            win_flag
        FROM main_analytics.fct_matchups
        WHERE week = {week}
        ORDER BY points DESC
    """).df()
    
    # Get updated standings
    standings = conn.execute("""
        SELECT 
            manager_name,
            wins,
            losses,
            round(points_for, 2) as points_for
        FROM main_analytics.fct_standings
        ORDER BY wins DESC, points_for DESC
        LIMIT 5
    """).df()
    
    # Get justice record updates
    justice = conn.execute("""
        SELECT 
            manager_name,
            actual_wins || '-' || actual_losses as actual_record,
            justice_wins || '-' || justice_losses as justice_record,
            luck_differential,
            luck_status
        FROM main_analytics.fct_justice_record
        ORDER BY luck_differential DESC
        LIMIT 3
    """).df()
    
    unlucky = conn.execute("""
        SELECT 
            manager_name,
            actual_wins || '-' || actual_losses as actual_record,
            justice_wins || '-' || justice_losses as justice_record,
            luck_differential,
            luck_status
        FROM main_analytics.fct_justice_record
        ORDER BY luck_differential ASC
        LIMIT 3
    """).df()
    
    # Build the report
    report = f"""
# 🏈 Morgan Bowl Week {week} Report
*Generated on {report_date}*

---

## 📊 Week {week} Results

### Highest Scorer of the Week
**{matchups.iloc[0]['manager_name']}** put up **{matchups.iloc[0]['points']} points**! 🔥

### Lowest Scorer of the Week
**{matchups.iloc[-1]['manager_name']}** only managed **{matchups.iloc[-1]['points']} points** 😬

### All Matchups
"""
    
    # Add matchup results
    for _, row in matchups.iterrows():
        result = "✅ W" if row['win_flag'] == 1 else "❌ L"
        report += f"\n- **{row['manager_name']}** {row['points']} pts vs **{row['opponent_manager_name']}** {row['opponent_points']} pts {result}"
    
    report += f"""

---

## 🏆 Top 5 Standings

"""
    
    for i, row in standings.iterrows():
        report += f"{i+1}. **{row['manager_name']}** ({row['wins']}-{row['losses']}) - {row['points_for']} PF\n"
    
    report += f"""

---

## 🍀 Luck Watch

### Luckiest Teams (Winning More Than They Deserve)
"""
    
    for _, row in justice.iterrows():
        report += f"- **{row['manager_name']}**: {row['actual_record']} actual, {row['justice_record']} deserved ({int(row['luck_differential']):+d}) {row['luck_status']}\n"
    
    report += """
### Unluckiest Teams (Losing More Than They Deserve)
"""
    
    for _, row in unlucky.iterrows():
        report += f"- **{row['manager_name']}**: {row['actual_record']} actual, {row['justice_record']} deserved ({int(row['luck_differential']):+d}) {row['luck_status']}\n"
    
    report += f"""

---

## 📈 Justice Record Explained

Each week, the **top 6 scorers** get a "justice win" and the **bottom 6** get a "justice loss". 
Your **justice record** shows what your record *should* be based on scoring performance.

**Luck Differential** = Actual Wins - Justice Wins
- Positive numbers = You're lucky! 🍀
- Negative numbers = You're unlucky! 😭

---

*View the full dashboard at: [Morgan Bowl Analytics](http://localhost:8501)*
*Data pipeline powered by DuckDB + DBT + GitLab CI/CD*
"""
    
    return report


def save_report(week: int, output_dir: str = "reports"):
    """Save the weekly report to a markdown file"""
    report = generate_weekly_report(week)
    
    output_path = Path(__file__).parent.parent / output_dir
    output_path.mkdir(exist_ok=True)
    
    filename = f"week_{week:02d}_report.md"
    filepath = output_path / filename
    
    with open(filepath, 'w') as f:
        f.write(report)
    
    print(f"✅ Report saved to: {filepath}")
    return filepath


def send_email_report(week: int, recipients: list[str]):
    """
    Send weekly report via email (requires email configuration)
    
    Example using Gmail:
    1. Set environment variables:
       - EMAIL_SENDER: your-email@gmail.com
       - EMAIL_PASSWORD: your-app-password (not your Gmail password!)
    
    2. Enable "App Passwords" in your Google account settings
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not sender or not password:
        print("⚠️  Email credentials not set. Set EMAIL_SENDER and EMAIL_PASSWORD environment variables.")
        return
    
    report = generate_weekly_report(week)
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🏈 Morgan Bowl Week {week} Report"
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)
    
    # Convert markdown to HTML (simple version)
    html = f"<pre>{report}</pre>"
    
    msg.attach(MIMEText(report, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
    
    print(f"✅ Email sent to {len(recipients)} recipients")


def post_to_slack(week: int, webhook_url: str = None):
    """
    Post weekly report to Slack
    
    1. Create a Slack webhook: https://api.slack.com/messaging/webhooks
    2. Set SLACK_WEBHOOK_URL environment variable or pass as argument
    """
    import json
    import urllib.request
    
    webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        print("⚠️  Slack webhook not configured. Set SLACK_WEBHOOK_URL environment variable.")
        return
    
    report = generate_weekly_report(week)
    
    payload = {
        "text": f"🏈 *Morgan Bowl Week {week} Report*",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": report
                }
            }
        ]
    }
    
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as response:
        print(f"✅ Posted to Slack: {response.status}")


if __name__ == "__main__":
    import sys
    
    # Get latest week from database
    db_path = Path(__file__).parent.parent / "data" / "warehouse.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    latest_week = conn.execute("SELECT MAX(week) FROM main_analytics.fct_matchups").fetchone()[0]
    
    week = int(sys.argv[1]) if len(sys.argv) > 1 else latest_week
    
    print(f"📝 Generating report for Week {week}...")
    
    # Save to file
    filepath = save_report(week)
    
    # Print to console
    print("\n" + "="*80)
    print(generate_weekly_report(week))
    print("="*80)
    
    # Uncomment to enable email or Slack:
    # send_email_report(week, ["friend1@example.com", "friend2@example.com"])
    # post_to_slack(week)
