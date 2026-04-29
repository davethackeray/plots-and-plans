# Daily Property Show - Deployment Guide

## Prerequisites
- Cloudflare account (free)
- GitHub repository
- Telegram bot credentials

## Step 1: Cloudflare Setup

### 1.1 Create D1 Database

```bash
# Install Wrangler CLI
npm install -g wrangler

# Authenticate
wrangler login

# Create D1 database
wrangler d1 create "daily-property-show-db" \
  --name="daily-property-show" \
  --region="WEUR"

# Output will include:
# - database_id: xxx
# - name: daily-property-show
```

### 1.2 Apply Schema

```bash
wrangler d1 execute \
  --database-name="daily-property-show" \
  --file=database/schema.sql
```

### 1.3 Create Worker (API)

```bash
wrangler init property-api
# Choose "Hello World" template, then replace main.py

# In property-api/wrangler.toml:
name = "property-api"
main = "src/index.py"
compatibility_date = "2024-01-01"

[[d1_databases]]
binding = "DB"
database_name = "daily-property-show"
database_id = "YOUR_DB_ID_HERE"

# Deploy
wrangler deploy
```

This gives you: `https://property-api.<your-account>.workers.dev`

## Step 2: GitHub Repository Setup

```bash
cd daily-show-system

# Initialize git
git init
git add .
git commit -m "Initial commit - Daily Property Show System"

# Create repo on GitHub (https://github.com/new)
# Then push:
git remote add origin https://github.com/<you>/daily-show-system.git
git push -u origin main
```

### 2.1 Configure Secrets

In GitHub repo → Settings → Secrets and variables → Actions:

Add these secrets:
- `TELEGRAM_BOT_TOKEN` (from @BotFather)
- `TELEGRAM_CHAT_ID` (your user/group ID)
- `CF_API_TOKEN` (Cloudflare API token with D1 edit rights)
- `CF_ACCOUNT_ID` (your Cloudflare account ID)

## Step 3: Local Testing

```bash
# Full pipeline test
python -m orchestrator

# Individual scraper test
python -m scrapers.tuscanitas

# Database check
python -c "from database import db; import asyncio; asyncio.run(db.init_database()); print('DB OK')"

# Dashboard test
python -m dashboard.app
# Browse to http://localhost:5000
```

## Step 4: Cloudflare Pages (Optional Frontend)

If you want a hosted dashboard:

```bash
# Create Pages project at https://dash.cloudflare.com
# Connect to your GitHub repo
# Build settings:
#   - Build command: (leave blank for static)
#   - Build output directory: dashboard/
#   - Environment variables: none needed

# Deploy
# Dashboard will be at: https://dashboard.roamtohome.pages.dev
```

## Step 5: First Production Run

### Manual Trigger (via GitHub UI)
1. Go to repository → Actions
2. Select "Daily Property Scrape & Select"
3. Click "Run workflow"
4. Check Telegram for notification

### Schedule Automation
Workflow already has cron: `0 6 * * *` (6 AM UTC).

## Step 6: Monitoring

### GitHub Actions Logs
- Repository → Actions → Latest run
- Check each scraper's output

### Telegram Alerts
- Daily summary sent automatically
- Errors also sent to same chat

### Database Inspection
```bash
# Connect to D1
wrangler d1 execute \
  --database-name="daily-property-show" \
  --command="SELECT COUNT(*) as total FROM properties;"

# View recent scrapes
wrangler d1 execute \
  --database-name="daily-property-show" \
  --command="SELECT * FROM scrape_log ORDER BY id DESC LIMIT 5;"
```

## Step 7: Backup Strategy

### Automated Backup (Daily)
Add to GitHub Actions:

```yaml
name: Daily Backup
on:
  schedule:
    - cron: '0 6 * * *'  # After scrape
jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Download DB artifact
        uses: actions/download-artifact@v4
        with:
          name: database-backup
      - name: Upload to Cloudflare R2
        run: |
          aws s3 cp database/properties.db s3://roamtohome-backups/$(date +%Y/%m/%Y-%m-%d.db)
```

Or local backup script:

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y-%m-%d)
cp database/properties.db "backups/properties-$DATE.db"
git add "backups/properties-$DATE.db"
git commit -m "Backup $DATE"
git push
```

## Troubleshooting Deployment

### GitHub Actions stuck/failing
- Check secrets are correct
- Verify Python version (3.11)
- Increase timeout for scrapers (longer than 10 min)

### D1 connection errors
- Ensure `wrangler.toml` has correct database ID
- Check Cloudflare API token permissions (needs Account > Workers & Pages Editor)

### Telegram not sending
- Verify bot token with `curl https://api.telegram.org/bot<token>/getMe`
- Confirm chat ID (can be numeric or @channel)
- Ensure bot has permission to send messages in chat

### Scrapers getting blocked
- Increase `scrape_delay` in each scraper
- Add rotating user-agents
- Consider using proxy service (BrightData, ScraperAPI)

### Database growing too fast
- Set up archival: move properties > 1 year old to separate table
- Prune price_history entries > 2 years
- Compress old scrape_logs

## Cost Control

Free tier limits:
- GitHub Actions: 2000 min/month → we use ~30 min/day = 900 min/month ✅
- Cloudflare D1: 5GB, 50k reads/day → with 300 properties/day, fine ✅
- Cloudflare Workers: 100k req/day → we use < 1000 ✅

Monitor in Cloudflare dashboard → Usage.

If you exceed:
- Actions: add billing → $0.008/min
- D1: $5/month for 5-25GB
- Workers: $5/month for 1M req

## Going Further

### Affiliate Tracking
Add UTM parameters to all listing URLs:
```
?utm_source=dailyshow&utm_medium=video&utm_campaign=YYYY-MM-DD
```

### RSS Feed Generation
Expose selected properties as RSS for YouTube auto-import:
```
/api/rss?date=YYYY-MM-DD
```

### YouTube Auto-Description
Auto-generate description template with all 6 links + timestamps.

---

**Need help?** Check logs in GitHub Actions or Telegram error messages.
