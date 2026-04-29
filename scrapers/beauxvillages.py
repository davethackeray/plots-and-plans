"""
Beaux Villages Immobilier Scraper
France - Dordogne & Southwest France
Specializes in character homes, renovation projects
Website: https://www.beauxvillages.com
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import async_playwright

from .base import BaseScraper
from models.property import Property


class BeauxVillagesScraper(BaseScraper):
    agency_name = "Beaux Villages Immobilier"
    base_url = "https://www.beauxvillages.com"
    country = "France"
    use_playwright = True  # Site is Joomla with some JS
    scrape_delay = 2.0

    agency_id = 2  # From our DB (need to verify)

    async def get_listing_urls(self, max_pages: int = 3) -> List[str]:
        """
        Beaux Villages listings are at /en/for-sale.html with pagination.
        Pagination: ?start=0, ?start=20, etc.
        """
        urls = []
        list_url = f"{self.base_url}/en/for-sale.html"

        logger.info(f"[BeauxVillages] Fetching from {list_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Accept cookies banner if present
            await page.goto(list_url, wait_until='networkidle', timeout=30000)
            try:
                await page.click('button:has-text("Allow cookies")', timeout=5000)
            except:
                pass  # No cookie banner

            for page_num in range(max_pages):
                try:
                    offset = page_num * 20
                    page_url = f"{list_url}?start={offset}"
                    await page.goto(page_url, wait_until='networkidle', timeout=30000)

                    # Wait for property grid (optional)
                    try:
                        await page.wait_for_selector('.property-item, .property-card, .item', timeout=5000)
                    except Exception:
                        logger.debug("Selector wait timed out, proceeding with current DOM")

                    # Extract links
                    links = await page.eval_on_selector_all(
                        'a[href*="/property/"], a[href*="/for-sale/"]',
                        'elements => elements.map(e => e.href)'
                    )

                    # Filter valid property URLs
                    for link in set(links):
                        if link not in urls and '/property/' in link:
                            urls.append(link)

                    logger.info(f"  Page {page_num + 1}: {len(links)} links, total {len(urls)}")

                    # Check if next page exists
                    next_link = await page.query_selector('a.next, .pagination-next')
                    if not next_link:
                        break

                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error on page {page_num}: {e}")
                    break

            await browser.close()

        logger.info(f"[BeauxVillages] Total URLs: {len(urls)}")
        return urls

    async def parse_property_page(self, html: str, url: str) -> Optional[Dict]:
        """Parse Beaux Villages property page."""
        soup = BeautifulSoup(html, 'html.parser')

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
        price_el = soup.find(class_=lambda c: c and 'price' in c.lower())
        if price_el:
            data['price'] = price_el.get_text(strip=True)
        else:
            # Search for price pattern
            price_match = re.search(r'€\s*([\d,]+)', html)
            if price_match:
                data['price'] = f"€{price_match.group(1)}"

        # Specs (BVI often uses definition lists)
        specs = self._extract_specs(soup)
        data.update(specs)

        # Description
        desc_el = soup.find(class_=lambda c: c and 'description' in c.lower())
        if desc_el:
            data['description'] = desc_el.get_text(strip=True)[:5000]
        else:
            paragraphs = soup.find_all('p')[:5]
            data['description'] = ' '.join(p.get_text(strip=True) for p in paragraphs)

        # Location
        breadcrumb = soup.find(class_=lambda c: c and 'breadcrumb' in c.lower())
        if breadcrumb:
            links = breadcrumb.find_all('a')
            if len(links) >= 2:
                data['region'] = links[-2].get_text(strip=True)
                data['city'] = links[-1].get_text(strip=True)

        # If no breadcrumb, parse from title
        if not data.get('city') and data.get('title'):
            # e.g., "Beautiful Farmhouse in Saint-Cyprien, Dordogne"
            parts = data['title'].split(',')
            if len(parts) >= 2:
                data['city'] = parts[-1].strip()
                data['region'] = 'Dordogne' if 'Dordogne' in data['title'] else 'South West France'

        # Images
        data['images'] = self._extract_images(soup)[:20]

        # Property type
        data['property_type'] = self._infer_type(data.get('title', ''), data.get('description', ''))

        # BVI often lists condition as "To renovate", "Habitable"
        if 'description' in data:
            desc_lower = data['description'].lower()
            if 'renovate' in desc_lower or 'to restore' in desc_lower:
                data['condition'] = 'renovation_needed'
            elif 'habitable' in desc_lower or 'in good condition' in desc_lower:
                data['condition'] = 'habitable'

        return data

    def _extract_ref(self, url: str) -> str:
        """Extract BVI property reference."""
        # URL pattern: /en/property/dordogne/farmhouse-for-sale-in-saint-cyprien_12345.html
        match = re.search(r'_(\d+)\.html', url)
        if match:
            return f"BVI-{match.group(1)}"
        return url.split('/')[-1].split('_')[0][:20]

    def _extract_specs(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract specs from BVI listing."""
        specs = {}

        # BVI uses various patterns
        selectors = [
            '.property-features li',
            '.specifications li',
            '.details li',
            'table.property-features tr',
        ]

        for selector in selectors:
            for item in soup.select(selector):
                text = item.get_text(strip=True).lower()

                if 'bedroom' in text or 'chambre' in text:
                    match = re.search(r'(\d+)', text)
                    if match:
                        specs['bedrooms'] = int(match.group(1))

                if 'bathroom' in text or 'bath' in text or 'salle de bain' in text:
                    match = re.search(r'(\d+)', text)
                    if match:
                        specs['bathrooms'] = int(match.group(1))

                if 'surface' in text and 'm' in text:
                    match = re.search(r'(\d+(?:[.,]\d+)?)\s*m', text)
                    if match:
                        area = match.group(1).replace(',', '.')
                        try:
                            specs['living_area'] = float(area)
                        except:
                            pass

                if 'land' in text or 'plot' in text or 'terrain' in text:
                    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:m|ha|hectare)?', text)
                    if match:
                        land = match.group(1).replace(',', '.')
                        try:
                            specs['plot_area'] = float(land)
                            if 'ha' in text.lower() or 'hectare' in text.lower():
                                specs['plot_area'] *= 10000
                        except:
                            pass

        return specs

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract images from Beaux Villages gallery."""
        images = []

        # Gallery images
        for img in soup.select('img[src*="property"], img[src*="gallery"]'):
            src = img.get('src') or img.get('data-src')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = self.base_url + src
                images.append(src)

        # Lightbox links
        for a in soup.select('a[href*=".jpg"], a[data-lightbox]'):
            href = a.get('href')
            if href and 'beauxvillages' in href:
                if href.startswith('/'):
                    href = self.base_url + href
                images.append(href)

        return list(dict.fromkeys(images))

    def _infer_type(self, title: str, description: str) -> str:
        """Infer property type from text."""
        text = (title + ' ' + description).lower()

        if 'farmhouse' in text or 'ferme' in text or 'mas' in text:
            return 'farmhouse'
        if 'château' in text or 'chateau' in text:
            return 'castle'
        if 'manor' in text or 'manoir' in text:
            return 'manor'
        if 'village house' in text or 'maison de village' in text:
            return 'village_house'
        if 'cottage' in text:
            return 'cottage'
        if 'renovation' in text and 'project' in text:
            return 'renovation_project'

        return 'house'
