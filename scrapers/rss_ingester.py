import aiohttp
import asyncio
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import re
from decimal import Decimal

from models.property import Property
from models.scorer import PropertyProcessor


class RSSFeedIngester:
    """
    Universal scraper that consumes standardized JSON feeds from our RSSHub instance.
    This replaces the bespoke Python scrapers for individual estate agents.
    """
    
    def __init__(self, rsshub_base_url: str, session: Optional[aiohttp.ClientSession] = None):
        self.rsshub_base_url = rsshub_base_url.rstrip('/')
        self.session = session
        self.processor = PropertyProcessor()
        self.stats = {'total': 0, 'new': 0, 'errors': 0}

    async def ingest_agency(self, agency_name: str, agency_id: int, route_path: str) -> List[Property]:
        """
        Fetch the JSON feed for a specific agency and convert to Property objects.
        """
        url = f"{self.rsshub_base_url}{route_path}.json"
        logger.info(f"[{agency_name}] Fetching feed: {url}")
        
        properties = []
        
        session_to_use = self.session or aiohttp.ClientSession()
        close_session = self.session is None
        
        try:
            async with session_to_use.get(url, timeout=60) as response:
                if response.status != 200:
                    logger.error(f"[{agency_name}] Failed to fetch feed: HTTP {response.status}")
                    self.stats['errors'] += 1
                    return properties
                    
                data = await response.json()
                items = data.get('items', [])
                logger.info(f"[{agency_name}] Found {len(items)} items in feed")
                
                for item in items:
                    try:
                        prop = self._parse_feed_item(item, agency_id)
                        if prop:
                            # Apply Heart-Rate scoring rules to description text
                            prop = self.processor.process(prop)
                            properties.append(prop)
                    except Exception as e:
                        logger.error(f"[{agency_name}] Error parsing item {item.get('url', 'unknown')}: {e}")
                        self.stats['errors'] += 1
                        
        except Exception as e:
            logger.error(f"[{agency_name}] Connection error: {e}")
            self.stats['errors'] += 1
        finally:
            if close_session:
                await session_to_use.close()
                
        self.stats['total'] += len(properties)
        return properties

    def _parse_feed_item(self, item: Dict[str, Any], agency_id: int) -> Optional[Property]:
        """
        Convert RSSHub JSON feed item to Property object.
        Extracts structured metadata embedded in content_html.
        """
        title = item.get('title', '')
        url = item.get('url', '')
        if not url:
            return None
            
        ref = item.get('id', '')
        if not ref:
            # Fallback to URL hash or end of path
            ref = url.split('/')[-1]
            
        # Parse the structured HTML we generate from RSSHub
        content_html = item.get('content_html', '')
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # 1. Metadata extraction
        meta_div = soup.find('div', class_='metadata')
        price = Decimal('0')
        beds = None
        baths = None
        location = ""
        
        if meta_div:
            price_span = meta_div.find('span', {'data-price': True})
            if price_span:
                try:
                    price_str = price_span['data-price']
                    price = Decimal(re.sub(r'[^\d.]', '', price_str))
                except:
                    pass
                    
            beds_span = meta_div.find('span', {'data-beds': True})
            if beds_span:
                try:
                    beds = int(beds_span['data-beds'])
                except:
                    pass
                    
            baths_span = meta_div.find('span', {'data-baths': True})
            if baths_span:
                try:
                    baths = int(baths_span['data-baths'])
                except:
                    pass
                    
            loc_span = meta_div.find('span', {'data-location': True})
            if loc_span:
                location = loc_span['data-location']
                
        # 2. Description extraction
        desc_div = soup.find('div', class_='description')
        description = desc_div.get_text(separator=' ', strip=True) if desc_div else ""
        
        # 3. Gallery extraction
        gallery_div = soup.find('div', class_='gallery')
        images = []
        if gallery_div:
            imgs = gallery_div.find_all('img')
            images = [img['src'] for img in imgs if img.get('src')]
            
        # Extract location details loosely
        city = ""
        region = ""
        country = ""
        if location:
            parts = [p.strip() for p in location.split(',')]
            if len(parts) >= 3:
                city, region, country = parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                city, region = parts[0], parts[1]
            else:
                city = location

        prop = Property(
            agency_id=agency_id,
            property_ref=str(ref)[:100],  # DB limit
            listing_url=url,
            title=title[:300],  # DB limit
            description=description,
            price=price,
            bedrooms=beds,
            bathrooms=baths,
            location_address=location,
            city=city,
            region=region,
            country=country,
            image_urls=images,
            primary_image_url=images[0] if images else ""
        )
        
        if item.get('date_published'):
            try:
                # Handle isoformat with or without Z
                date_str = item['date_published'].replace('Z', '+00:00')
                prop.date_listed = datetime.fromisoformat(date_str)
            except ValueError:
                pass
                
        return prop
