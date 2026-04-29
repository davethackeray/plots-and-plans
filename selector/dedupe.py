"""
Deduplication Engine - Identifies duplicate or near-duplicate properties.
"""

import hashlib
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

from ..models.property import Property


@dataclass
class DuplicateMatch:
    """Represents a detected duplicate."""
    property_a: Property
    property_b: Property
    match_type: str  # 'exact', 'fuzzy_address', 'same_agent_ref'
    confidence: float  # 0.0 - 1.0


class Deduplicator:
    """Detects and handles duplicate property listings."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def fingerprint(self, prop: Property) -> str:
        """
        Generate stable fingerprint for exact deduplication.
        Based on: agency + ref + normalized address.
        """
        norm_addr = self._normalize_address(prop.location_address)
        key = f"{prop.agency_id}|{prop.property_ref}|{norm_addr}|{int(prop.price)}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _normalize_address(self, address: str) -> str:
        """
        Normalize address for fuzzy comparison.
        Remove numbers, punctuation, common words.
        """
        import re
        if not address:
            return ""

        # Lowercase, remove extra whitespace
        addr = address.lower().strip()

        # Remove unit/apt numbers
        addr = re.sub(r'\b(apt|unit|appt|flat|#)\s*\w+', '', addr)

        # Remove street numbers
        addr = re.sub(r'\b\d+\b', '', addr)

        # Remove common filler words
        filler = ['de', 'la', 'le', 'du', 'des', 'et', 'en', 'near', 'close to']
        words = [w for w in addr.split() if w not in filler]

        return ' '.join(words)

    def is_duplicate(self, prop1: Property, prop2: Property) -> Optional[DuplicateMatch]:
        """
        Check if two properties are duplicates.
        Returns DuplicateMatch if yes, None if unique.
        """
        # 1. Exact match on agency ref (same agent, same listing)
        if prop1.agency_id == prop2.agency_id and prop1.property_ref == prop2.property_ref:
            return DuplicateMatch(
                prop1, prop2, 'exact_agent_ref', 1.0
            )

        # 2. Exact fingerprint match (cross-agent dupes)
        fp1 = self.fingerprint(prop1)
        fp2 = self.fingerprint(prop2)
        if fp1 == fp2:
            return DuplicateMatch(
                prop1, prop2, 'exact_fingerprint', 1.0
            )

        # 3. Fuzzy address match
        addr1 = self._normalize_address(prop1.location_address)
        addr2 = self._normalize_address(prop2.location_address)

        if addr1 and addr2:
            similarity = SequenceMatcher(None, addr1, addr2).ratio()
            if similarity >= self.similarity_threshold:
                # Also check price is similar (within 10%)
                price_diff = abs(prop1.price - prop2.price) / max(prop1.price, prop2.price)
                if price_diff < 0.10:
                    return DuplicateMatch(
                        prop1, prop2, 'fuzzy_address', similarity
                    )

        # 4. Same coordinates (exact location)
        if (prop1.latitude and prop2.latitude and
            prop1.longitude and prop2.longitude):
            lat_diff = abs(prop1.latitude - prop2.latitude)
            lon_diff = abs(prop1.longitude - prop2.longitude)
            if lat_diff < 0.0001 and lon_diff < 0.0001:  # ~10 meters
                return DuplicateMatch(
                    prop1, prop2, 'same_coordinates', 0.99
                )

        return None

    def deduplicate_list(self, properties: List[Property]) -> List[Property]:
        """
        Remove duplicates from a list of properties.
        Keeps the one with most complete data / highest heart-rate score.
        """
        if not properties:
            return []

        # Sort by score descending, completeness ascending (more complete first)
        def sort_key(p):
            completeness = (
                int(bool(p.description)) +
                int(bool(p.bedrooms)) +
                int(bool(p.price)) +
                int(bool(p.images))
            )
            return (-p.heart_rate_score, -completeness)

        sorted_props = sorted(properties, key=sort_key)

        unique = []
        seen_fingerprints = set()

        for prop in sorted_props:
            fp = self.fingerprint(prop)

            if fp not in seen_fingerprints:
                unique.append(prop)
                seen_fingerprints.add(fp)
            # else: skip duplicate

        return unique


class PropertyValidator:
    """Validates property data quality before scoring."""

    REQUIRED_FIELDS = ['title', 'price', 'listing_url', 'city', 'country']

    def validate(self, prop: Property) -> Tuple[bool, List[str]]:
        """
        Check if property has minimum required data.
        Returns (is_valid, list_of_errors).
        """
        errors = []

        if not prop.title or len(prop.title) < 5:
            errors.append("Title too short or missing")

        if not prop.price or prop.price <= 0:
            errors.append("Invalid price")

        if not prop.listing_url:
            errors.append("Missing listing URL")

        if not prop.city:
            errors.append("Missing city")

        if not prop.country:
            errors.append("Missing country")

        # Warning-level issues (not fatal)
        if not prop.bedrooms:
            pass  # Acceptable (studio, loft)

        if not prop.image_urls:
            errors.append("No images - property needs photos")

        return len(errors) == 0, errors
