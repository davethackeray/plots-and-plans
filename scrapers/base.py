"""
Base scraper class - all agency-specific scrapers inherit from this.
"""

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

import aiohttp
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from loguru import logger

from models.property import Property
from models.scorer import PropertyProcessor


class BaseScraper(ABC):
    """
    Abstract base class for all estate agency scrapers.

    Each scraper must implement:
    - get_listing_urls(): Return list of property page URLs to scrape
    - parse_property_page(html, url): Extract property data from page

    The base class handles rate limiting, caching, retries.
    """

    agency_name = "Base"
    base_url = ""
    country = "Unknown"
    scrape_delay = 2.0  # seconds between requests
    max_pages = 5  # pagination limit
    use_playwright = False  # Set True if site requires JS

    def __init__(self, session: aiohttp.ClientSession = None):
        self.session = session
        self.processor = PropertyProcessor()
        self.stats = {
            'pages_scraped': 0,
            'properties_found': 0,
            'errors': 0,
        }

    @abstractmethod
    async def get_listing_urls(self, max_pages: int = None) -> List[str]:
        """
        Fetch property listing page URLs.
        Returns list of full URLs to individual property pages.
        """
        pass

    @abstractmethod
    async def parse_property_page(self, html: str, url: str) -> Optional[Dict]:
        """
        Parse individual property page HTML.
        Return dict with raw property data matching Property fields.
        Return None if page invalid or property sold.
        """
        pass

    async def scrape(self, max_properties: int = 50) -> List[Property]:
        """
        Main scraping workflow.
        """
        logger.info(f"[{self.agency_name}] Starting scrape")

        properties = []
        urls = await self.get_listing_urls()

        for i, url in enumerate(urls[:max_properties]):
            try:
                # Respect rate limiting
                await asyncio.sleep(self.scrape_delay)

                # Fetch page (Playwright or requests)
                if self.use_playwright:
                    html = await self._fetch_with_playwright(url)
                else:
                    html = await self._fetch(url)

                if not html:
                    continue

                # Parse property data
                raw_data = await self.parse_property_page(html, url)
                if not raw_data:
                    continue

                # Add metadata
                raw_data['url'] = url
                raw_data['country'] = self.country
                raw_data['date_scraped'] = datetime.now().isoformat()

                # Convert to Property object
                prop = self.processor.process(raw_data, agency_id=self._get_agency_id())
                properties.append(prop)

                self.stats['properties_found'] += 1
                logger.debug(f"  ✓ {prop.title[:40]} - {prop.price}")

            except Exception as e:
                logger.error(f"  ✗ Error on {url}: {e}")
                self.stats['errors'] += 1

        logger.info(f"[{self.agency_name}] Scrape complete: {len(properties)} properties")
        return properties

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL with aiohttp session."""
        if not self.session:
            return None

        headers = {
            'User-Agent': 'DailyPropertyShow/1.0 (compatible; +https://roamtohome.com)'
        }

        try:
            async with self.session.get(url, headers=headers, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    logger.warning(f"HTTP {resp.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Fetch error {url}: {e}")
            return None

    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright (for JS-heavy sites)."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                content = await page.content()
                await browser.close()
                return content
            except Exception as e:
                logger.error(f"Playwright error {url}: {e}")
                await browser.close()
                return None

    def _get_agency_id(self) -> int:
        """
        Get agency ID from database (should be pre-loaded).
        Override or implement lookup.
        """
        return 1  # Placeholder

    def to_feature(self, raw: Dict, key: str, default=None):
        """Helper: safely extract nested dict value."""
        return raw.get(key, default)


# Convenience function for running scraper directly
async def run_scraper(scraper_class, max_properties: int = 50) -> List[Property]:
    """Run a scraper class and return properties."""
    async with aiohttp.ClientSession() as session:
        scraper = scraper_class(session)
        return await scraper.scrape(max_properties)
