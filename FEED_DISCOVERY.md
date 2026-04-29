# RSS/API Discovery Guide for Estate Agents

## Objective

Systematically check each estate agent website for existing RSS feeds, XML sitemaps, or API endpoints to replace/suppment scraping.

## Why This Matters

- **Efficiency:** Pull data directly vs. scraping HTML
- **Reliability:** Official feeds are stable, won't break with site redesigns
- **Politeness:** Respect agent's servers - they推送数据 to us
- **Partnership:** Using their feed shows respect and can lead to formal partnerships

## Discovery Checklist for Each Agency

### 1. Check Standard RSS Feed Locations

Test these URLs (replace `example.com`):

```
https://www.example.com/rss
https://www.example.com/feed
https://www.example.com/feed/rss
https://www.example.com/feed/atom
https://www.example.com/rss.xml
https://www.example.com/feed.xml
https://www.example.com/rss/feed
https://www.example.com/index.php?format=feed&type=rss
```

### 2. Look for Sitemaps

```
https://www.example.com/sitemap.xml
https://www.example.com/sitemap_index.xml
https://www.example.com/sitemap-properties.xml
https://www.example.com/sitemap-news.xml
```

Sitemaps often list all property URLs even if no feed exists.

### 3. Inspect Page Source

Search HTML source for:
- `<link rel="alternate" type="application/rss+xml"` (RSS autodiscovery)
- `<link rel="alternate" type="application/atom+xml"` (Atom feed)
- `<!-- feeds -->` comments
- JavaScript variables like `rssUrl`, `feedUrl`

### 4. Check Footer & Navigation

Look for links labeled:
- "RSS", "Feed", "Subscribe"
- "News", "Blog", "Properties"
- "API", "Developers", "Integration"
- "Partners", "Affiliates"

### 5. Developer Tools Inspection

1. Open browser DevTools (F12)
2. Network tab → Filter by "XHR" or "fetch"
3. Reload page → Look for API calls returning JSON
4. Check `application/json` responses

### 6. Common Real Estate Platform Feeds

Many agents use these platforms (check if site is on them):

- **WordPress:** `/?feed=rss2` or `/feed/`
- **Joomla:** `/index.php?option=com_content&view=category&id=XX&format=feed`
- **Drupal:** `/rss.xml`
- **Wix:** `/blog-feed.xml`
- **Squarespace:** `/rss.xml` or `/blog/rss.xml`

## Agency-Specific Investigation

### Italy

**Tuscanitas (Divine Tuscany)**
- Base: https://www.tuscanitas.com
- Likely: Custom PHP site, may have RSS at `/en/rss` or `/en/villas-farmhouses/feed`
- Check: Footer for "News" or "Blog" feed

**Marche Country Homes**
- Base: https://www.marchecountryhomes.com
- Platform: Possibly WordPress
- Test: `/feed/`, `/rss/`, `/blog/feed`

**Case in Langa**
- Base: https://www.caseinlanga.it
- Likely: Custom Italian site - check `sitemap.xml`

**Agenzia Il Casale**
- Base: https://www.agenziailcasale.it
- Platform: Unknown - inspect footer for RSS icon

### France

**Beaux Villages**
- Base: https://www.beauxvillages.com
- Platform: Joomla (observed)
- Joomla RSS: `/index.php?format=feed` or `/en/for-sale?format=feed`
- Already has some JSON endpoints visible in network tab

**Leggett Immobilier**
- Base: https://www.leggett-immo.com
- Platform: WordPress likely
- Check: `/feed/`, `/properties/feed`

**Agence Newton**
- Base: https://www.agencenewton.com
- Platform: Custom - check `sitemap.xml`

**Romantic Houses**
- Base: https://www.romantichouses.com
- Platform: Unknown - inspect

### Spain

**Aldeas Abandonadas**
- Base: https://www.aldeasabandonadas.com
- Platform: Custom PHP
- Check: Footer for RSS, `sitemap.xml`

**Buscomasia**
- Base: https://www.buscomasia.com
- Platform: Possibly WordPress
- Test: `/feed/`, `/rss/`

**Lançois Doval**
- Base: https://www.lancoisdoval.es
- Platform: Custom - check footer

**Gaia Inmobiliaria Rural**
- Base: https://www.gaiainmobiliariarural.com
- Platform: Unknown

**Rustica Estates**
- Base: https://www.rusticaestates.com
- Platform: WordPress likely

**Rusur**
- Base: https://www.rusur.es
- Platform: Unknown

### Portugal

**PortugalRur**
- Base: https://www.portugalrur.pt
- Platform: Unknown

**Entreportas**
- Base: https://www.entreportas.pt
- Platform: Unknown

## Automated Discovery Script

Create a script to test all agencies automatically:

```python
import requests
import xml.etree.ElementTree as ET
from typing import List, Tuple

class FeedDiscovery:
    """Test common feed locations for an agency website."""

    COMMON_PATHS = [
        '/rss', '/feed', '/feed/rss', '/feed/atom',
        '/rss.xml', '/feed.xml', '/atom.xml',
        '/rss/feed', '/blog/feed', '/blog/rss',
        '/rss2', '/rss20',
        '/?format=feed', '/?feed=rss2',
        '/sitemap.xml', '/sitemap-index.xml',
        '/en/rss', '/en/feed', '/en/rss.xml',
    ]

    def check_url(self, base_url: str, path: str) -> Tuple[bool, str]:
        """Test if URL exists and is a feed."""
        url = base_url.rstrip('/') + path
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                if 'xml' in content_type or 'rss' in content_type:
                    return True, f"Feed found: {url}"
                # Could be HTML sitemap - still useful
                return False, f"Sitemap found: {url}"
        except:
            pass
        return False, ""

    def discover_feeds(self, base_url: str) -> List[str]:
        """Test all common paths and return any feeds found."""
        found = []
        for path in self.COMMON_PATHS:
            is_feed, msg = self.check_url(base_url, path)
            if is_feed:
                found.append(base_url.rstrip('/') + path)
        return found

# Usage:
discoverer = FeedDiscovery()
feeds = discoverer.discover_feeds('https://www.example.com')
print(feeds)
```

## What to Look For

### RSS 2.0 Feed
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Agency Properties</title>
    <item>
      <title>Beautiful Farmhouse</title>
      <link>https://example.com/property/123</link>
      <description>...</description>
      <price>€185,000</price>
      <image>https://example.com/image.jpg</image>
      <location>Saint-Cyprien, Dordogne</location>
    </item>
  </channel>
</rss>
```

### JSON API
```json
{
  "properties": [
    {
      "id": 123,
      "title": "Beautiful Farmhouse",
      "url": "https://...",
      "price": 185000,
      "bedrooms": 4,
      "bathrooms": 2,
      "type": "farmhouse",
      "condition": "renovation_needed",
      "description": "...",
      "images": ["url1", "url2"],
      "location": {
        "city": "Saint-Cyprien",
        "region": "Dordogne",
        "country": "France",
        "lat": 44.888,
        "lon": 0.123
      }
    }
  ]
}
```

### Atom Feed
Similar to RSS but different XML structure.

## Action Plan

1. **Manual check first** - Quick visual inspection of each agency site
2. **Automated scan** - Run discovery script against all 13 agencies
3. **Prioritize feeds**:
   - Full property data (price, beds, baths, description) → HIGH
   - Just links/URLs → MEDIUM (still useful for change detection)
   - Blog/news only → LOW (not property listings)
4. **Implement feed parsers**:
   - Replace scraper with feed reader if feed found
   - Keep scraper as fallback
   - Log which source (feed vs scrape) for each property

## Benefits

If we find feeds for even 3-4 agencies:
- Reduce scrape time from ~30 min to ~5 min
- Get more complete data (often includes features we'd miss scraping)
- Avoid blocking/rate limiting issues
- Build goodwill with agents ("we use your RSS feed")

## Next Steps

1. Run manual check on all 13 agencies (10 minutes each)
2. Document findings in this file
3. Update scrapers to use feeds where available
4. Set up RSS-to-DB sync as separate GitHub Action (runs hourly)

---

**Status:** Not started  
**Owner:** Dave  
**Target completion:** Before full scraper deployment
