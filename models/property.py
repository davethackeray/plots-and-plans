"""
Property data model with Heart-Rate scoring.
Represents a single real estate listing with all attributes needed for selection.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
import json


@dataclass
class Property:
    """A real estate property listing with scoring attributes."""

    # Core identifiers
    id: Optional[int] = None
    agency_id: int = 0
    property_ref: str = ""
    listing_url: str = ""

    # Basic info
    title: str = ""
    description: str = ""

    # Financial
    price: Decimal = field(default_factory=lambda: Decimal('0'))
    currency: str = "EUR"
    price_history: List[Dict] = field(default_factory=list)

    # Physical attributes
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: str = ""  # farmhouse, village_house, cottage, ruin, mill, etc.
    condition: str = ""  # habitable, renovation_needed, shell, luxury
    plot_area_m2: Optional[Decimal] = None
    living_area_m2: Optional[Decimal] = None
    land_area_ha: Optional[Decimal] = None  # for Escapism scoring

    # Location
    location_address: str = ""
    city: str = ""
    region: str = ""
    country: str = ""
    postcode: str = ""
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    geo_cluster: str = ""  # e.g., "dordogne-central"

    # Heart-Rate scores (0-100)
    sublime_escapism_score: int = 0
    authentic_bones_score: int = 0
    sanctuary_capacity_score: int = 0
    multiplier_score: float = 1.0  # 0.1-1.0
    heart_rate_score: int = 0  # final weighted score

    # Feature flags (boolean flags for algorithm)
    has_sea_view: bool = False
    has_mountain_view: bool = False
    has_valley_view: bool = False
    neighbor_distance_m: int = 0
    has_exposed_beams: bool = False
    has_original_stone_floors: bool = False
    has_functional_fireplaces: int = 0
    has_structural_stone_walls: bool = False
    has_wooden_ceilings: bool = False
    construction_year: Optional[int] = None
    outbuilding_count: int = 0
    has_annex_potential: bool = False
    has_pool: bool = False
    has_separate_entrance: bool = False
    is_set_back_from_road: bool = False

    # Media
    image_urls: List[str] = field(default_factory=list)
    primary_image_url: str = ""
    has_floorplan: bool = False
    has_video_tour: bool = False

    # Tracking
    date_listed: Optional[datetime] = None
    date_scraped: datetime = field(default_factory=datetime.now)
    last_verified: datetime = field(default_factory=datetime.now)
    is_still_for_sale: bool = True
    featured_count: int = 0

    # Deduplication
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)
        # Convert datetime to ISO string
        if self.date_listed:
            data['date_listed'] = self.date_listed.isoformat()
        data['date_scraped'] = self.date_scraped.isoformat()
        data['last_verified'] = self.last_verified.isoformat()
        # JSON fields need to be serialized
        for field in ['price_history', 'image_urls', 'talking_points']:
            if field in data and isinstance(data[field], list):
                data[field] = json.dumps(data[field])
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Property':
        """Create Property from database row."""
        # Handle datetime parsing
        for date_field in ['date_listed', 'date_scraped', 'last_verified']:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        # Parse JSON fields
        for json_field in ['price_history', 'image_urls', 'talking_points']:
            if data.get(json_field) and isinstance(data[json_field], str):
                try:
                    data[json_field] = json.loads(data[json_field])
                except json.JSONDecodeError:
                    data[json_field] = []

        return cls(**data)

    def calculate_fingerprint(self) -> str:
        """
        Create stable fingerprint for deduplication.
        Based on normalized address + price + bedrooms.
        """
        import hashlib
        import re

        # Normalize address (remove numbers, capitalize)
        norm_addr = re.sub(r'\d+', '', self.location_address).upper().strip()
        norm_city = self.city.upper().strip()

        key = f"{norm_addr}|{norm_city}|{self.price}|{self.bedrooms}"
        self.fingerprint = hashlib.md5(key.encode()).hexdigest()[:16]
        return self.fingerprint

    def calculate_heart_rate_score(self) -> int:
        """
        The core algorithm - score this property's 'irresistible' factor.
        Returns 0-1000 final score.
        """
        # 1. Sublime Escapism Index (0-100)
        sublime = self._calc_sublime_score()

        # 2. Authentic Bones Score (0-100)
        authentic = self._calc_authentic_score()

        # 3. Sanctuary Capacity (0-100)
        sanctuary = self._calc_sanctuary_score()

        # 4. Manageable Project Multiplier (0.1-1.0)
        multiplier = self._calc_multiplier()

        # Weighted final score
        raw = (
            sublime * 0.35 +
            authentic * 0.30 +
            sanctuary * 0.20
        ) * multiplier

        # Add novelty bonus for unique features
        novelty_bonus = self._calc_novelty_bonus() * 0.15
        final_score = int(raw + novelty_bonus)

        # Cap at 1000 (for display friendliness)
        self.heart_rate_score = min(1000, final_score)

        # Store component scores for transparency
        self.sublime_escapism_score = sublime
        self.authentic_bones_score = authentic
        self.sanctuary_capacity_score = sanctuary
        self.multiplier_score = multiplier

        return self.heart_rate_score

    def _calc_sublime_score(self) -> int:
        """Score based on views, land, and privacy."""
        score = 0

        # Views (heaviest weight)
        if self.has_sea_view:
            score += 40
        if self.has_mountain_view:
            score += 35
        if self.has_valley_view:
            score += 30

        # Privacy (neighbor distance)
        if self.neighbor_distance_m > 100:
            score += 20
        elif self.neighbor_distance_m > 50:
            score += 10

        # Land size (in hectares)
        if self.land_area_ha:
            land_score = min(25, self.land_area_ha * 5)  # max 25 pts
            score += int(land_score)

        return min(100, score)

    def _calc_authentic_score(self) -> int:
        """Score based on historic character features."""
        score = 0

        if self.has_exposed_beams:
            score += 25
        if self.has_original_stone_floors:
            score += 25
        if self.has_functional_fireplaces:
            score += 15 * min(3, self.has_functional_fireplaces)  # up to 45
        if self.has_structural_stone_walls:
            score += 20
        if self.has_wooden_ceilings:
            score += 15

        # Age bonus
        if self.construction_year and self.construction_year < 1900:
            score += 20
        elif self.construction_year and self.construction_year < 1950:
            score += 10

        return min(100, score)

    def _calc_sanctuary_score(self) -> int:
        """Score based on space for dreams (shala, sauna, studio)."""
        score = 0

        # Outbuildings (barns, granges)
        if self.outbuilding_count >= 3:
            score += 60
        elif self.outbuilding_count == 2:
            score += 40
        elif self.outbuilding_count == 1:
            score += 20

        # Annex potential
        if self.has_annex_potential:
            score += 25

        # Flat land for building
        if self.plot_area_m2 and self.plot_area_m2 > 1000:
            score += 20

        # Pool (already built luxury)
        if self.has_pool:
            score += 15

        # Separate entrance (for gite/B&B)
        if self.has_separate_entrance:
            score += 15

        # Set back from road (peace & quiet)
        if self.is_set_back_from_road:
            score += 10

        return min(100, score)

    def _calc_multiplier(self) -> float:
        """
        Safety check - reduce score if property is unmanageable.
        Returns 0.1 - 1.0 multiplier.
        """
        mult = 1.0

        # Affordability ceiling (tiered penalty)
        if self.price > 250000:
            mult *= 0.3  # Too expensive
        elif self.price < 30000:
            mult *= 0.7  # Suspiciously cheap
        elif self.price < 80000:
            mult *= 0.9  # Budget-friendly bonus

        # Condition check (structural soundness)
        if self.condition in ['shell', 'ruin']:
            mult *= 0.2  # Major rebuild needed
        elif self.condition == 'renovation_needed':
            mult *= 0.7  # Moderate work OK
        elif self.condition == 'habitable':
            mult *= 1.0  # Ready to live
        # luxury condition gets 1.0 too (already done)

        # Size sanity check
        if self.bedrooms and self.bedrooms > 8:
            mult *= 0.5  # Mansion = high upkeep
        if self.living_area_m2 and self.living_area_m2 > 500:
            mult *= 0.7  # Too large

        return round(max(0.1, mult), 2)

    def _calc_novelty_bonus(self) -> int:
        """Bonus for truly unique features."""
        bonus = 0

        # Check description for unique keywords
        if self.description:
            desc = self.description.lower()
            unique_keywords = [
                'mill', 'watermill', 'windmill', 'tower', 'castle',
                'cave', 'troglodyte', 'chapel', 'church', 'lighthouse',
                'holy', 'romantic', 'rare', 'unique', 'once-in-a-lifetime'
            ]
            for kw in unique_keywords:
                if kw in desc:
                    bonus += 15
                    break

        return bonus

    def get_segment(self) -> str:
        """
        Determine which of the 6 show segments this property best fits.
        Returns segment label string.
        """
        scores = {
            'sublime': self.sublime_escapism_score,
            'authentic': self.authentic_bones_score,
            'sanctuary': self.sanctuary_capacity_score,
        }

        # Quick Win: affordable + fast renovation potential
        is_quick_win = (
            self.price and self.price < 80000 and
            self.condition in ['habitable', 'renovation_needed'] and
            self.authentic_bones_score >= 60
        )

        # Unique Wonder: has novelty bonus + unusual type
        is_unique = (
            self._calc_novelty_bonus() > 30 or
            self.property_type in ['mill', 'tower', 'castle', 'cave', 'ruin']
        )

        # Determine primary segment by highest pillar score
        primary_pillar = max(scores, key=scores.get)

        if is_unique:
            return "The Unique Wonder"
        elif is_quick_win:
            return "The Quick Win"
        elif scores['sublime'] >= 75:
            return "The Sublime View"
        elif scores['authentic'] >= 75:
            return "The Authentic Bones"
        elif scores['sanctuary'] >= 70:
            return "The Sanctuary Plot"
        else:
            return "The Balanced Gem"

    def to_show_dict(self) -> Dict:
        """Convert to show-ready dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'price': float(self.price) if self.price else 0,
            'currency': self.currency,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'property_type': self.property_type,
            'condition': self.condition,
            'plot_area_m2': float(self.plot_area_m2) if self.plot_area_m2 else None,
            'living_area_m2': float(self.living_area_m2) if self.living_area_m2 else None,
            'location': f"{self.city}, {self.region}, {self.country}",
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'listing_url': self.listing_url,
            'image_urls': self.image_urls,
            'primary_image': self.primary_image_url,
            'description': self.description[:500] if self.description else "",
            'heart_rate_score': self.heart_rate_score,
            'segment': self.get_segment(),
            'scores': {
                'sublime': self.sublime_escapism_score,
                'authentic': self.authentic_bones_score,
                'sanctuary': self.sanctuary_capacity_score,
                'multiplier': self.multiplier_score,
            }
        }
