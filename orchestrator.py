"""
Daily Show Orchestrator - Main workflow automation.
Runs daily: scrape → score → select → notify.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import sys

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import aiohttp

from database import db
from models.property import Property
from models.scorer import PropertyProcessor, HeartRateScorer
from scrapers.base import BaseScraper
from scrapers.tuscanitas import TuscanitasScraper
from scrapers.beauxvillages import BeauxVillagesScraper
from selector.engine import PropertySelector
from notifier.bot import TelegramNotifier


# Registry of all active scrapers
SCRAPER_REGISTRY = [
    TuscanitasScraper,
    BeauxVillagesScraper,
    # Add more scrapers here as implemented
    # MarcheCountryHomesScraper,
    # CaseInLangaScraper,
    # ...
]


class DailyShowOrchestrator:
    """
    Coordinates the entire daily property selection pipeline.
    - Runs scrapers
    - Stores in database
    - Selects 6 properties
    - Notifies curator
    - Logs results
    """

    def __init__(self, send_telegram: bool = True):
        self.selector = PropertySelector()
        self.notifier = TelegramNotifier() if send_telegram else None
        self.scrape_results = {
            'total_found': 0,
            'new_properties': 0,
            'updated_properties': 0,
            'errors': 0,
            'scraper_stats': {},
        }

    async def run_daily_pipeline(self, target_date: datetime = None) -> Dict:
        """
        Execute complete daily pipeline.
        1. Scrape all agencies
        2. Score & deduplicate
        3. Select 6 properties
        4. Notify curator
        """
        logger.info("=" * 60)
        logger.info("DAILY PROPERTY SHOW - PIPELINE STARTING")
        logger.info("=" * 60)

        target_date = target_date or datetime.now()

        # PHASE 1: SCRAPING
        logger.info("\n📡 PHASE 1: Scraping agencies...")
        all_properties = await self._scrape_all_agencies()

        logger.info(f"✓ Total properties scraped: {len(all_properties)}")

        # PHASE 2: STORE IN DATABASE
        logger.info("\n💾 PHASE 2: Storing in database...")
        new_count, updated_count = await self._store_properties(all_properties)
        logger.info(f"✓ New: {new_count}, Updated: {updated_count}")

        # PHASE 3: SELECTION
        logger.info("\n🎯 PHASE 3: Running Heart-Rate selection...")
        selection = await self.selector.select_for_date(target_date)

        if 'error' in selection:
            logger.error(f"Selection failed: {selection['error']}")
            return {'status': 'error', 'message': selection['error']}

        selected_props = selection['selected']
        logger.info(f"✓ Selected {len(selected_props)} properties")
        logger.info(f"  Segments: {selection['metadata']['segments']}")
        logger.info(f"  Avg Score: {selection['metadata']['avg_score']:.1f}")

        # PHASE 4: NOTIFICATION
        if self.notifier and selected_props:
            logger.info("\n📱 PHASE 4: Sending notification...")
            message = self._format_telegram_message(selection)
            await self.notifier.send(message)
            logger.info("✓ Notification sent")

        # PHASE 5: LOGGING
        await self._log_run(target_date, selection, new_count, updated_count)

        logger.info("\n✅ PIPELINE COMPLETE\n")

        return {
            'status': 'success',
            'date': target_date.strftime('%Y-%m-%d'),
            'selected': selected_props,
            'metadata': selection['metadata'],
            'scrape_stats': self.scrape_results,
        }

    async def _scrape_all_agencies(self) -> List[Property]:
        """Run all registered scrapers in parallel (respecting per-domain delays)."""
        all_properties = []

        for scraper_cls in SCRAPER_REGISTRY:
            scraper_name = scraper_cls.agency_name
            logger.info(f"\n  [{scraper_name}] Starting scraper")

            try:
                # Run scraper with timeout
                async with aiohttp.ClientSession() as session:
                    scraper = scraper_cls(session)
                    properties = await asyncio.wait_for(
                        scraper.scrape(max_properties=50),
                        timeout=300  # 5 min max per scraper
                    )
                    all_properties.extend(properties)

                    self.scrape_results['scraper_stats'][scraper_name] = {
                        'found': len(properties),
                        'errors': scraper.stats['errors'],
                    }

            except asyncio.TimeoutError:
                logger.error(f"[{scraper_name}] TIMEOUT after 5 minutes")
                self.scrape_results['errors'] += 1
            except Exception as e:
                logger.error(f"[{scraper_name}] ERROR: {e}")
                self.scrape_results['errors'] += 1

        self.scrape_results['total_found'] = len(all_properties)
        return all_properties

    async def _store_properties(self, properties: List[Property]) -> tuple[int, int]:
        """
        Store properties in database.
        - New: INSERT
        - Existing: UPDATE if price/status changed
        Returns (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0

        conn = await db.connect()

        for prop in properties:
            # Check if exists by listing_url
            existing = await db.fetch_one(
                "SELECT * FROM properties WHERE listing_url = ?",
                (prop.listing_url,)
            )

            prop_dict = prop.to_dict()

            if existing:
                # Update existing
                await conn.execute("""
                    UPDATE properties
                    SET price = ?,
                        is_still_for_sale = ?,
                        last_verified = ?,
                        heart_rate_score = ?,
                        image_urls = ?,
                        bedrooms = ?,
                        bathrooms = ?,
                        condition = ?
                    WHERE id = ?
                """, (
                    float(prop.price) if prop.price else 0,
                    prop.is_still_for_sale,
                    prop.last_verified.isoformat(),
                    prop.heart_rate_score,
                    json.dumps(prop.image_urls),
                    prop.bedrooms,
                    prop.bathrooms,
                    prop.condition,
                    existing['id']
                ))
                updated_count += 1
            else:
                # Insert new
                prop_id = await db.insert("""
                    INSERT INTO properties (
                        agency_id, property_ref, listing_url, title, description,
                        price, currency, bedrooms, bathrooms, property_type, condition,
                        plot_area_m2, living_area_m2, land_area_ha,
                        location_address, city, region, country, postcode,
                        latitude, longitude, geo_cluster,
                        image_urls, primary_image_url,
                        date_listed, date_scraped, last_verified,
                        fingerprint, is_still_for_sale,
                        sublime_escapism_score, authentic_bones_score,
                        sanctuary_capacity_score, multiplier_score,
                        heart_rate_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prop.agency_id,
                    prop.property_ref,
                    prop.listing_url,
                    prop.title,
                    prop.description,
                    float(prop.price) if prop.price else 0,
                    prop.currency,
                    prop.bedrooms,
                    prop.bathrooms,
                    prop.property_type,
                    prop.condition,
                    float(prop.plot_area_m2) if prop.plot_area_m2 else None,
                    float(prop.living_area_m2) if prop.living_area_m2 else None,
                    float(prop.land_area_ha) if prop.land_area_ha else None,
                    prop.location_address,
                    prop.city,
                    prop.region,
                    prop.country,
                    prop.postcode,
                    float(prop.latitude) if prop.latitude else None,
                    float(prop.longitude) if prop.longitude else None,
                    prop.geo_cluster,
                    json.dumps(prop.image_urls),
                    prop.primary_image_url,
                    prop.date_listed.isoformat() if prop.date_listed else None,
                    prop.date_scraped.isoformat(),
                    prop.last_verified.isoformat(),
                    prop.fingerprint,
                    prop.is_still_for_sale,
                    prop.sublime_escapism_score,
                    prop.authentic_bones_score,
                    prop.sanctuary_capacity_score,
                    prop.multiplier_score,
                    prop.heart_rate_score,
                ))
                new_count += 1

        await conn.commit()
        return new_count, updated_count

    def _format_telegram_message(self, selection: Dict) -> str:
        """Format selection results as Telegram message."""
        date = selection['show_date']
        props = selection['selected']
        meta = selection['metadata']

        lines = [
            f"🏡 Daily Property Show - {date}",
            f"📊 Avg Score: {meta['avg_score']:.0f}/1000",
            "",
        ]

        for i, prop in enumerate(props, 1):
            segment = prop.get('segment', 'Property')
            price = f"€{prop['price']:,.0f}" if prop.get('price') else "Price on request"
            lines.append(
                f"{i}. {segment}\n"
                f"   {prop['title'][:50]}...\n"
                f"   💰 {price} | 🛏️ {prop.get('bedrooms', '?')} bed | {prop['city']}, {prop['country']}\n"
                f"   🔗 {prop['listing_url']}\n"
            )

        # Add nearby episode hints
        if selection.get('nearby_episodes'):
            lines.append("\n📍 Nearby past episodes:")
            for prop_id, episodes in selection['nearby_episodes'].items():
                for ep in episodes[:1]:  # Just one per property
                    lines.append(f"   • {ep['city']} (Show {ep['show_id']})")

        lines.append(f"\n✅ {meta['property_count']} candidates considered")
        lines.append(f"🌍 Countries: {', '.join(meta['countries'])}")

        return "\n".join(lines)

    async def _log_run(self, date: datetime, selection: Dict, new: int, updated: int):
        """Log run to database for audit."""
        await db.execute("""
            INSERT INTO scrape_log (
                agency_id, scrape_start, scrape_end,
                properties_found, properties_new, properties_updated,
                status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            0,  # 0 = all agencies
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            self.scrape_results['total_found'],
            new,
            updated,
            'success',
            f"Selected {len(selection['selected'])} properties for show"
        ))


# CLI entry point
async def main():
    """Run daily pipeline from command line."""
    orchestrator = DailyShowOrchestrator(send_telegram=True)
    result = await orchestrator.run_daily_pipeline()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
