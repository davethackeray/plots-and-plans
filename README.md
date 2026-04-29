# Daily Property Show System

Automated property discovery and curation for the OddLot daily real estate show. Scrapes boutique European estate agents, scores properties with the "Heart-Rate" emotional impact algorithm, and delivers 6 diverse properties daily.

**Status:** Alpha - In active development

## Tech Stack (100% Free Tier)

| Component | Technology | Cost |
|-----------|------------|------|
| Frontend/Dashboard | GitHub Pages (static) | $0 |
| Database | Cloudflare D1 (SQLite, 5GB) | $0 |
| Scraping | GitHub Actions (2000 min/month) | $0 |
| API | Cloudflare Workers (100k req/day) | $0 |
| Notifications | Telegram Bot API | $0 |

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Git
- Telegram Bot (get from [@BotFather](https://t.me/BotFather))

### Setup

```bash
# Clone & cd
cd roamtohome/daily-show-system

# Create virtualenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env:
#   TELEGRAM_BOT_TOKEN=your_token
#   TELEGRAM_CHAT_ID=your_chat_id

# Initialize database
python -m database.init

# Test scraper (Tuscanitas only)
python -m scrapers.tuscanitas

# Run full pipeline
python -m orchestrator
```

If successful, you'll see:
```
✅ Daily Property Show Pipeline Complete
📊 Avg Score: 452/1000
📱 Notification sent
```

## Project Structure

```
daily-show-system/
├── scrapers/               # Agency-specific scrapers (13 total)
│   ├── base.py            # BaseScraper (async, rate-limited)
│   ├── tuscanitas.py      # Italy - Tuscany (DONE)
│   ├── beauxvillages.py   # France - Dordogne (DONE)
│   ├── romantic_houses.py # France - Coming soon
│   └── ...
├── database/              # SQLite schema & connection
│   ├── schema.sql
│   ├── __init__.py
│   └── queries.py
├── models/                # Data models & algorithms
│   ├── property.py        # Property class + Heart-Rate scoring
│   └── scorer.py          # Emotional impact engine
├── selector/              # Selection logic
│   ├── engine.py          # Daily pick algorithm
│   ├── dedupe.py          # Duplicate detection
│   └── diversity.py       # Geographic/type diversity
├── dashboard/             # Admin dashboard (Flask/FastAPI)
│   ├── app.py
│   ├── static/
│   ├── templates/
│   └── production_sheet.py
├── notifier/              # Telegram alerts
│   └── bot.py
├── orchestrator.py        # Main pipeline coordinator
├── requirements.txt
├── .env.example
└── README.md
```

## Heart-Rate Algorithm

Properties scored across 3 emotional pillars:

| Pillar | Weight | What it measures | Key features |
|--------|--------|-----------------|--------------|
| **Sublime Escapism** | 35% | Can you imagine yourself here? | Sea/mountain/valley views, privacy, vast land |
| **Authentic Bones** | 30% | Does it already have soul? | Exposed beams, stone floors, fireplaces, historic |
| **Sanctuary Capacity** | 20% | Space to build your dreams | Outbuildings, annex potential, flat land |

× **Manageable Project Multiplier** (0.1-1.0) - safety check on price & condition

**Total range:** 0-1000 points

### Scored Features (extracted from descriptions)

```python
# Sublime Escapism
has_sea_view → +40 pts
has_mountain_view → +35 pts
land_area_ha * 5 → up to +25 pts

# Authentic Bones
has_exposed_beams → +25 pts
has_original_stone_floors → +25 pts
has_functional_fireplaces → +15 each
has_structural_stone_walls → +20 pts

# Sanctuary Capacity
outbuilding_count * 20 → up to +60 pts
has_annex_potential → +25 pts
has_separate_entrance → +15 pts
```

## Daily Workflow

```
6:00 AM  → GitHub Action triggers scrape (13 agencies)
6:30 AM  → Properties stored, deduplicated
7:00 AM  → Heart-Rate scoring & selection
7:30 AM  → Telegram sent to curator with 6 candidates
8:00 AM  → Curator reviews dashboard, swaps 0-2 properties
9:00 AM  → Production sheet exported (CSV with Google Maps)
10:00 AM → Ready to shoot
```

## 6 Show Segments

Each daily show presents 6 categorically different properties:

| Segment | Trigger | Appeal | Price Range |
|---------|---------|--------|-------------|
| 1. The Sublime View | Highest Escapism score | "This is the view you'll wake up to" | Any |
| 2. The Authentic Bones | Highest Authentic score | "It already has its soul" | Any |
| 3. The Sanctuary Plot | Highest Sanctuary score | "Build your dream within the dream" | Any |
| 4. The Quick Win | Fast renovation + affordable | "Move in 3 months, not 3 years" | <€80k |
| 5. The Unique Wonder | Most unusual feature | "You've never seen anything like this" | Any |
| 6. The Balanced Gem | High across all pillars | "Everything you need, nothing you don't" | Any |

**Mix rules enforced automatically:** No 2+ properties from same country/day; no same city within 7 days.

## Dashboard Features

**Local Review Interface** (`python -m dashboard.app` → http://localhost:5000)

- View today's 6 picks with full property data
- See Heart-Rate breakdown (sublime/authentic/sanctuary)
- One-click swap any property with backup pool
- Generate production-ready CSV
- View nearby past episodes for cross-promotion

## Adding New Agency Scrapers

1. Create `scrapers/agency_name.py`
2. Inherit from `BaseScraper`
3. Implement:
   - `agency_name`, `base_url`, `country`, `agency_id`
   - `get_listing_urls()` - fetch property page URLs
   - `parse_property_page(html, url)` - extract fields dict
4. Register in `orchestrator.py` SCRAPER_REGISTRY
5. Test: `python -m scrapers.agency_name`

See `scrapers/tuscanitas.py` for complete example.

## Database Schema

Core tables:
- `properties` - all listings with Heart-Rate scores
- `shows` - episodes produced
- `showed_properties` - deduplication log
- `agencies` - scraper registry
- `price_history` - track changes
- `scrape_log` - audit trail

See `database/schema.sql` for full DDL.

## Deployment

### Local (Development)
```bash
python -m venv venv
pip install -r requirements.txt
python -m database.init
python -m orchestrator
```

### GitHub Actions (Daily Scrapes)
Workflow: `.github/workflows/daily-property-scrape.yml`

- Runs daily 6:00 AM UTC
- Executes scrapers → selects → commits DB
- Uploads production sheet as artifact
- Can be manually triggered with `workflow_dispatch`

### Cloudflare D1 (Production DB)
In production, replace local SQLite with Cloudflare D1:

```bash
# Install Wrangler
npm install -g wrangler

# Create D1 database
wrangler d1 create "daily-property-show"

# Update wrangler.toml with DB details

# Migrate schema
wrangler d1 execute --file database/schema.sql
```

See `DEPLOY.md` for full Cloudflare setup.

## Telegram Commands (Bot)

Once configured, the bot supports:

- `/today` - Show today's 6 properties
- `/stats` - Pipeline statistics
- `/swap <id>` - Request property swap
- `/refresh` - Force re-scrape & re-select

(Commands need bot polling implementation - TODO)

## Troubleshooting

### Scraper blocks
**Symptom:** HTTP 403/429 errors
**Fix:** Increase `scrape_delay`, rotate user-agents, add proxy support

### Duplicate properties
**Symptom:** Same property appears in multiple shows
**Fix:** Check `_filter_recent()` - ensure 90-day dedup window active

### Missing scores
**Symptom:** heart_rate_score = 0
**Fix:** Verify description field contains keywords; scraper must populate emotional features

### Database locked
**Symptom:** SQLite "database is locked"
**Fix:** Use WAL mode (already enabled), ensure single writer

## Cost Projections

| Service | Free Tier | When You Pay |
|---------|-----------|--------------|
| GitHub Actions | 2000 min/month | $0.008/min → ~$40 for 24/7 |
| Cloudflare D1 | 5GB, 50k reads/day | $0.50/GB + $0.50/100k reads |
| Cloudflare Workers | 100k req/day | $0.50/million requests |
| Telegram | Unlimited | Free |

**Expected monthly cost:** $0 for first 6-12 months (prototype phase).

## Next Steps

1. ✅ Database schema complete
2. ✅ Scraper base class + Tuscanitas
3. ✅ Selection engine + Heart-Rate algorithm
4. ⏳ Add remaining 12 agency scrapers
5. ⏳ Dashboard refinement + swap UI
6. ⏳ Telegram bot commands
7. ⏳ Cloudflare D1 migration
8. ⏳ YouTube integration (auto-desc with affiliate links)

## Contributing

This is a solo project. Architecture decisions are final.

## License

Private - All rights reserved

---

Built with ❤️ by Kilo for OddLot. The dream is alive.
