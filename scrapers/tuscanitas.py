"""
Tuscanitas (Divine Tuscany) Scraper
Italy - Tuscany region
Specializes in luxury farmhouses, historic properties, vineyards
Website: https://www.tuscanitas.com
"""

import asyncio
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper
from ..models.property import Property


class TuscanitasScraper(BaseScraper):
    agency_name = "Tuscanitas"
    base_url = "https://www.tuscanitas.com"
    country = "Italy"
    use_playwright = True  # Site uses JavaScript rendering
    scrape_delay = 2.5  # Polite delay

    # Agency ID from DB (must match agencies table)
    agency_id = 4

    async def get_listing_urls(self, max_pages: int = 3) -> List[str]:
        """
        Get property listing URLs from search pages.
        Tuscanitas: /en/villas-farmhouses.html paginated
        """
        urls = []
        list_url = f"{self.base_url}/en/villas-farmhouses.html"

        logger.info(f"[Tuscanitas] Fetching listing pages from {list_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for page_num in range(1, max_pages + 1):
                try:
                    # Navigate to page (with pagination parameter if needed)
                    page_url = list_url if page_num == 1 else f"{list_url}?page={page_num}"
                    await page.goto(page_url, wait_until='networkidle', timeout=30000)

                    # Wait for property grid
                    await page.wait_for_selector('.property-listing, .property-card, .item', timeout=10000)

                    # Extract links
                    links = await page.eval_on_selector_all(
                        'a[href*="/properties/"], a[href*="/villas-farmhouses/"]',
                        'elements => elements.map(e => e.href)'
                    )

                    # Dedupe
                    for link in set(links):
                        if link not in urls and 'properties' in link:
                            urls.append(link)

                    logger.info(f"  Page {page_num}: found {len(links)} property links")

                    # Check if next page exists
                    next_btn = await page.query_selector('a.next, .pagination-next')
                    if not next_btn:
                        break

                except Exception as e:
                    logger.error(f"Error on page {page_num}: {e}")
                    break

            await browser.close()

        logger.info(f"[Tuscanitas] Total property URLs: {len(urls)}")
        return urls

    async def parse_property_page(self, html: str, url: str) -> Optional[Dict]:
        """
        Parse individual property page.
        Tuscanitas property page structure:
        - Title: <h1 class="property-title">
        - Price: <span class="price">
        - Details: table with beds/baths/area
        - Description: <div class="description">
        - Images: in gallery
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Basic check - is this a valid property page?
        if not soup.find('h1'):
            return None

        data = {
            'ref': self._extract_ref(url),
            'agency_id': self.agency_id,
        }

        # Title
        title_tag = soup.find('h1')
        if title_tag:
            data['title'] = title_tag.get_text(strip=True)

        # Price
        price_tag = soup.find(class_=lambda c: c and 'price' in c.lower())
        if price_tag:
            data['price'] = price_tag.get_text(strip=True)
        else:
            # Try regex search
            price_match = re.search(r'€\s*([\d,]+)', html)
            if price_match:
                data['price'] = f"€{price_match.group(1)}"

        # Beds/Baths/Area from spec table
        specs = self._extract_specs(soup)
        data.update(specs)

        # Description
        desc_div = soup.find(class_=lambda c: c and 'description' in c.lower())
        if desc_div:
            data['description'] = desc_div.get_text(strip=True)[:5000]
        else:
            # Fallback: all paragraph text
            paragraphs = soup.find_all('p')
            data['description'] = ' '.join(p.get_text(strip=True) for p in paragraphs[:5])

        # Location (city/region)
        location = self._extract_location(soup, data.get('title', ''))
        data.update(location)

        # Coordinates (if available)
        latlon = self._extract_coordinates(soup)
        if latlon:
            data['latitude'] = latlon[0]
            data['longitude'] = latlon[1]

        # Images
        images = self._extract_images(soup)
        data['images'] = images[:20]  # Cap at 20

        # Property type
        data['property_type'] = self._infer_type(data.get('title', ''), data.get('description', ''))

        # Images-based feature extraction (we'll also parse description)
        # Note: Heart-Rate features will be extracted by scorer from description

        return data

    def _extract_ref(self, url: str) -> str:
        """Extract property reference from URL."""
        # URL like: /en/villas-farmhouses/p123-some-name.html
        match = re.search(r'p(\d+)', url)
        if match:
            return f"TUS-{match.group(1)}"
        return url.split('/')[-1].split('.')[0][:20]

    def _extract_specs(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract bedrooms, bathrooms, area from spec table."""
        specs = {}

        # Look for spec table/list
        spec_selectors = [
            '.property-features li',
            '.specs li',
            '.details-list li',
            'table tr',
        ]

        for selector in spec_selectors:
            items = soup.select(selector)
            if not items:
                continue

            for item in items:
                text = item.get_text(strip=True).lower()

                # Bedrooms
                if 'bed' in text or 'camera' in text or 'camera da letto' in text:
                    match = re.search(r'(\d+)', text)
                    if match:
                        specs['bedrooms'] = int(match.group(1))

                # Bathrooms
                if 'bath' in text or 'bagno' in text:
                    match = re.search(r'(\d+)', text)
                    if match:
                        specs['bathrooms'] = int(match.group(1))

                # Area
                if 'sqm' in text or 'm²' in text or 'mq' in text or 'surface' in text:
                    match = re.search(r'(\d+(?:[.,]\d+)?)\s*m', text)
                    if match:
                        area = match.group(1).replace(',', '.')
                        try:
                            specs['living_area'] = float(area)
                        except:
                            pass

                # Plot/land area
                if 'land' in text or 'plot' in text or 'hectare' in text or 'ha' in text:
                    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(ha|hectare|hectares)?', text)
                    if match:
                        land = match.group(1).replace(',', '.')
                        try:
                            specs['plot_area'] = float(land)
                            # Convert ha to m² if needed
                            if 'ha' in text.lower():
                                specs['plot_area'] *= 10000
                        except:
                            pass

        return specs

    def _extract_location(self, soup: BeautifulSoup, title: str) -> Dict[str, str]:
        """Extract city, region, address."""
        location = {'city': '', 'region': '', 'address': '', 'postcode': ''}

        # Try breadcrumb
        breadcrumb = soup.find(class_=lambda c: c and 'breadcrumb' in c.lower())
        if breadcrumb:
            links = breadcrumb.find_all('a')
            # Typically: Home > Tuscany > Siena > Property
            if len(links) >= 3:
                location['region'] = links[-2].get_text(strip=True)
                location['city'] = links[-1].get_text(strip=True)

        # Try to parse from title
        if not location['city'] and title:
            # "Beautiful Farmhouse in Montepulciano, Tuscany"
            parts = title.split(',')
            if len(parts) >= 2:
                location['city'] = parts[-1].strip()
                location['region'] = parts[-2].strip() if len(parts) >= 3 else 'Tuscany'

        # Try location meta tag
        geo = soup.find('meta', attrs={'name': 'geo.position'})
        if geo:
            content = geo.get('content', '')
            if content:
                lat, lon = content.split(';')
                location['latitude'] = float(lat.strip())
                location['longitude'] = float(lon.strip())

        return location

    def _extract_coordinates(self, soup: BeautifulSoup) -> Optional[tuple]:
        """Extract lat/lon from embedded map or meta tags."""
        # Check for geo meta
        geo = soup.find('meta', attrs={'name': 'geo.position'})
        if geo:
            try:
                lat, lon = geo['content'].split(';')
                return float(lat.strip()), float(lon.strip())
            except:
                pass

        # Check for Google Maps iframe
        iframe = soup.find('iframe', src=re.compile(r'google.com/maps'))
        if iframe:
            match = re.search(r'q=([-\d.]+),([-\d.]+)', iframe['src'])
            if match:
                return float(match.group(1)), float(match.group(2))

        return None

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract all property image URLs."""
        images = []

        # Gallery images (various selectors)
        selectors = [
            '.gallery img',
            '.property-images img',
            '.carousel img',
            'img[src*="property"]',
            'img[src*="photo"]',
        ]

        for sel in selectors:
            for img in soup.select(sel):
                src = img.get('src') or img.get('data-src')
                if src:
                    # Make absolute URL
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = self.base_url + src
                    images.append(src)

        # Deduplicate
        return list(dict.fromkeys(images))

    def _infer_type(self, title: str, description: str) -> str:
        """Infer property type from title/description."""
        text = (title + ' ' + description).lower()

        if 'farmhouse' in text or 'casale' in text or 'masseria' in text:
            return 'farmhouse'
        if 'villa' in text:
            return 'villa'
        if 'castle' in text or 'château' in text or 'castello' in text:
            return 'castle'
        if 'mill' in text or 'mulino' in text:
            return 'mill'
        if 'tower' in text or 'torre' in text:
            return 'tower'
        if 'apartment' in text or 'flat' in text:
            return 'apartment'
        if 'ruin' in text or 'shell' in text:
            return 'ruin'
        if 'village house' in text or 'casa' in text:
            return 'village_house'

        return 'house'
