"""
Heart-Rate Scoring Engine.
Implements the 3-pillar algorithm for property evaluation.
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from .property import Property


class HeartRateScorer:
    """
    Scores properties based on emotional impact (not just specs).
    Three pillars: Sublime Escapism, Authentic Bones, Sanctuary Capacity.
    """

    # Keyword patterns for feature extraction from descriptions
    VIEW_PATTERNS = [
        (r'\bsea view\b', 'sea'),
        (r'\bocean view\b', 'sea'),
        (r'\bpanoramic\b', 'panoramic'),
        (r'\bvalley view\b', 'valley'),
        (r'\bmountain view\b', 'mountain'),
        (r'\boverlooking\b', 'overlooking'),
        (r'\bvista\b', 'vista'),
        (r'\bview of\b', 'view'),
    ]

    AUTHENTIC_PATTERNS = [
        (r'\bexposed beams?\b', 'beams'),
        (r'\boriginal floors?\b', 'original_floors'),
        (r'\bterracotta\b', 'terracotta'),
        (r'\bstone floors?\b', 'stone_floors'),
        (r'\bfireplace\b', 'fireplace'),
        (r'\bcheminée\b', 'fireplace'),
        (r'\bhearthe?\b', 'fireplace'),
        (r'\bstone walls?\b', 'stone_walls'),
        (r'\bwooden ceilings?\b', 'wooden_ceilings'),
        (r'\bbeamed ceilings?\b', 'beams'),
        (r'\bparquet\b', 'parquet'),
        (r'\boriginal features\b', 'original'),
    ]

    SANCTUARY_PATTERNS = [
        (r'\boutbuildings?\b', 'outbuilding'),
        (r'\bbarn\b', 'outbuilding'),
        (r'\bgrange\b', 'outbuilding'),
        (r'\bdépendance\b', 'outbuilding'),
        (r'\bhangar\b', 'outbuilding'),
        (r'\bworkshop\b', 'workshop'),
        (r'\bstudio\b', 'annex'),
        (r'\bannex\b', 'annex'),
        (r'\bseparate entrance\b', 'separate_entrance'),
        (r'\bgîte\b', 'gite'),
        (r'\bguest house\b', 'annex'),
        (r'\bbuilding plot\b', 'land'),
        (r'\bplot of land\b', 'land'),
        (r'\bpotential to build\b', 'land'),
    ]

    CONDITION_KEYWORDS = {
        'habitable': ['habitable', 'liveable', 'liveable', 'in good condition'],
        'renovation_needed': ['renovate', 'update', 'refresh', 'needs work', 'to modernize'],
        'shell': ['shell', 'empty', 'needs total renovation', 'to rebuild'],
        'luxury': ['luxury', 'high-end', 'prestige', 'prestigious']
    }

    def __init__(self):
        self.feature_cache = {}

    def score_property(self, prop: Property) -> Property:
        """
        Main entry point - extract features and calculate all scores.
        Modifies property in-place and returns it.
        """
        if prop.description:
            desc = prop.description.lower()
            self._extract_features(prop, desc)

        prop.calculate_heart_rate_score()
        return prop

    def _extract_features(self, prop: Property, description: str):
        """Extract emotional features from listing description."""

        # Extract views
        for pattern, feature in self.VIEW_PATTERNS:
            if re.search(pattern, description, re.IGNORECASE):
                if feature == 'sea':
                    prop.has_sea_view = True
                elif feature == 'mountain':
                    prop.has_mountain_view = True
                elif feature in ['valley', 'panoramic', 'overlooking', 'vista', 'view']:
                    prop.has_valley_view = True

        # Extract authentic features
        for pattern, feature in self.AUTHENTIC_PATTERNS:
            if re.search(pattern, description, re.IGNORECASE):
                if feature == 'beams':
                    prop.has_exposed_beams = True
                elif feature in ['original_floors', 'terracotta']:
                    prop.has_original_stone_floors = True
                elif feature == 'fireplace':
                    prop.has_functional_fireplaces += 1
                elif feature == 'stone_walls':
                    prop.has_structural_stone_walls = True
                elif feature in ['wooden_ceilings', 'beamed_ceilings', 'parquet']:
                    prop.has_wooden_ceilings = True

        # Extract sanctuary features
        outbuildings = 0
        for pattern, feature in self.SANCTUARY_PATTERNS:
            matches = re.findall(pattern, description, re.IGNORECASE)
            if matches:
                if feature == 'outbuilding':
                    outbuildings += len(matches)
                elif feature == 'annex':
                    prop.has_annex_potential = True
                elif feature == 'separate_entrance':
                    prop.has_separate_entrance = True
                elif feature == 'gite':
                    prop.has_annex_potential = True
                prop.outbuilding_count = max(prop.outbuilding_count, outbuildings)

        # Condition detection
        for cond, keywords in self.CONDITION_KEYWORDS.items():
            for kw in keywords:
                if kw in description:
                    prop.condition = cond
                    break

        # Parse year from description if present
        year_match = re.search(r'\b(18|19)\d{2}\b', description)
        if year_match:
            prop.construction_year = int(year_match.group())

    def batch_score(self, properties: list[Property]) -> list[Property]:
        """Score multiple properties."""
        return [self.score_property(p) for p in properties]


class PropertyProcessor:
    """
    Processes raw scraped data into scored Property objects.
    Normalizes data across different scrapers.
    """

    # Mapping of scraper-specific types to our canonical types
    TYPE_MAPPING = {
        # Italian
        'casale': 'farmhouse',
        'villa': 'villa',
        'palazzo': 'townhouse',
        'masseria': 'farmhouse',
        'trulli': 'unique',
        # French
        'mas': 'farmhouse',
        'bastide': 'villa',
        'château': 'castle',
        'maison': 'house',
        'longère': 'farmhouse',
        'grange': 'ruin',  # barn conversion
        # Spanish
        'cortijo': 'farmhouse',
        'finca': 'country_estate',
        'masia': 'farmhouse',
        'casa': 'house',
        'pazo': 'manor',
        # Portuguese
        'quinta': 'country_estate',
        'moradia': 'house',
        'monte': 'farmhouse',
    }

    def normalize_property_type(self, raw_type: str, country: str) -> str:
        """Convert agency-specific type to our canonical."""
        raw = raw_type.lower().strip()
        return self.TYPE_MAPPING.get(raw, raw)

    def extract_price(self, price_str: str) -> Decimal:
        """Extract numeric price from string like '€125,000' or '125000'."""
        import re
        clean = re.sub(r'[^\d.,]', '', price_str)
        # Handle European format (comma as decimal, period as thousand)
        if clean.count(',') == 1 and clean.count('.') == 0:
            # European: 125.000,50 -> 125000.50
            clean = clean.replace('.', '').replace(',', '.')
        else:
            # US/UK: remove commas
            clean = clean.replace(',', '')
        try:
            return Decimal(clean)
        except:
            return Decimal('0')

    def parse_area(self, area_str: str) -> Optional[Decimal]:
        """Extract area in m² from string."""
        import re
        if not area_str:
            return None
        match = re.search(r'(\d+(?:[.,]\d+)?)', str(area_str))
        if match:
            try:
                val = match.group(1).replace(',', '.').replace(' ', '')
                return Decimal(val)
            except:
                pass
        return None

    def create_fingerprint(self, prop: Property) -> str:
        """
        Generate stable hash for deduplication.
        Based on: normalized address + price + beds + agency.
        """
        import hashlib

        norm_addr = ' '.join(
            w.upper() for w in prop.location_address.split()
            if len(w) > 2 and w.lower() not in ['de', 'la', 'le', 'du', 'des', 'et']
        )
        key = f"{norm_addr}|{prop.city}|{prop.price}|{prop.bedrooms}|{prop.agency_id}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def process(self, raw_data: Dict, agency_id: int) -> Property:
        """
        Convert raw scraper output into Property object.
        Raw data dict should contain all fields scraped from listing.
        """
        prop = Property()

        # Required fields
        prop.agency_id = agency_id
        prop.property_ref = raw_data.get('ref', '')
        prop.listing_url = raw_data.get('url', '')

        # Basic info
        prop.title = raw_data.get('title', '')[:300]
        prop.description = raw_data.get('description', '')

        # Price
        price_str = raw_data.get('price', '')
        prop.price = self.extract_price(price_str)

        # Physical
        prop.bedrooms = raw_data.get('bedrooms')
        prop.bathrooms = raw_data.get('bathrooms')
        prop.property_type = self.normalize_property_type(
            raw_data.get('property_type', ''),
            raw_data.get('country', '')
        )
        prop.condition = raw_data.get('condition', '').lower()

        # Areas
        prop.plot_area_m2 = self.parse_area(raw_data.get('plot_area'))
        prop.living_area_m2 = self.parse_area(raw_data.get('living_area'))
        if prop.plot_area_m2:
            prop.land_area_ha = prop.plot_area_m2 / 10000  # m² to hectares

        # Location
        prop.location_address = raw_data.get('address', '')
        prop.city = raw_data.get('city', '')
        prop.region = raw_data.get('region', '')
        prop.country = raw_data.get('country', '')
        prop.postcode = raw_data.get('postcode', '')
        prop.latitude = raw_data.get('latitude')
        prop.longitude = raw_data.get('longitude')

        # Images
        prop.image_urls = raw_data.get('images', [])
        if prop.image_urls:
            prop.primary_image_url = prop.image_urls[0]

        # Dates
        prop.date_listed = raw_data.get('date_listed')
        # date_scraped set by default

        # Generate fingerprint
        prop.calculate_fingerprint()

        return prop
