"""
Selection Engine - Picks 6 daily properties using Heart-Rate algorithm.
Ensures diversity, avoids duplicates, and creates balanced show.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

from ..database import db
from ..models.property import Property
from .scorer import HeartRateScorer


class SelectionEngine:
    """
    Daily property selection logic.
    Runs Heart-Rate algorithm, ensures variety, prevents repeats.
    """

    def __init__(self):
        self.scorer = HeartRateScorer()

    async def select_daily_properties(
        self,
        available_properties: List[Property],
        show_date: datetime,
        preferences: Dict = None
    ) -> Tuple[List[Property], Dict]:
        """
        Main selection method.

        Args:
            available_properties: List of all available properties
            show_date: Date of the show
            preferences: Optional curator preferences (price range, etc.)

        Returns:
            (selected_properties, metadata)
        """
        preferences = preferences or {}

        # 1. Filter to eligible candidates
        candidates = self._filter_eligible(available_properties)

        # 2. Remove recently shown (90-day window)
        candidates = await self._exclude_recent(candidates, days=90)

        # 3. Apply curator preferences (if any)
        if preferences:
            candidates = self._apply_preferences(candidates, preferences)

        # 4. Score all candidates
        candidates = self.scorer.batch_score(candidates)

        # 5. Ensure geographic diversity (avoid same cluster)
        candidates = self._enforce_geo_diversity(candidates)

        # 6. Pick 6 properties - one per segment
        selected = self._pick_by_segment(candidates)

        # 7. Backup selection if not enough
        if len(selected) < 6:
            need = 6 - len(selected)
            backups = self._pick_backups(candidates, selected, need)
            selected.extend(backups)

        # 8. Find nearby past episodes for cross-promotion
        nearby_refs = await self._find_nearby_episodes(selected)

        metadata = {
            'date': show_date.strftime('%Y-%m-%d'),
            'total_candidates': len(candidates),
            'selected_count': len(selected),
            'segments': [p.get_segment() for p in selected],
            'nearby_episodes': nearby_refs,
            'avg_score': sum(p.heart_rate_score for p in selected) / 6,
        }

        return selected, metadata

    def _filter_eligible(self, properties: List[Property]) -> List[Property]:
        """
        Filter properties to eligible candidates based on baseline criteria.
        """
        filtered = []

        for prop in properties:
            # Must be for sale
            if not prop.is_still_for_sale:
                continue

            # Must have essential data
            if not prop.price or prop.price <= 0:
                continue
            if not prop.bedrooms or prop.bedrooms < 1:
                continue

            # Price ceiling - no mega-mansions
            if prop.price > 500000:
                continue

            # Condition must not be 'sold' or 'off_market'
            if prop.condition in ['sold', 'off_market', 'withdrawn']:
                continue

            # Must have listing URL (valid listing)
            if not prop.listing_url:
                continue

            filtered.append(prop)

        return filtered

    async def _exclude_recent(self, properties: List[Property], days: int = 90) -> List[Property]:
        """
        Remove properties shown in the last N days.
        Uses database check against showed_properties.
        """
        if not properties:
            return []

        prop_ids = [p.id for p in properties if p.id]

        if not prop_ids:
            return properties

        # Query DB for recently shown property IDs
        cutoff = datetime.now() - timedelta(days=days)
        query = """
            SELECT DISTINCT property_id
            FROM showed_properties sp
            JOIN shows s ON sp.show_id = s.id
            WHERE s.show_date >= ?
        """
        async with db.get_cursor() as cur:
            await cur.execute(query, (cutoff.strftime('%Y-%m-%d'),))
            rows = await cur.fetchall()
            recent_ids = {row['property_id'] for row in rows}

        # Filter out
        return [p for p in properties if p.id not in recent_ids]

    def _apply_preferences(self, properties: List[Property], prefs: Dict) -> List[Property]:
        """Apply curator's preferences (price range, excluded regions, etc.)."""
        filtered = properties

        # Price range
        if 'min_price' in prefs:
            filtered = [p for p in filtered if p.price >= prefs['min_price']]
        if 'max_price' in prefs:
            filtered = [p for p in filtered if p.price <= prefs['max_price']]

        # Countries to include/exclude
        if 'include_countries' in prefs:
            filtered = [p for p in filtered if p.country in prefs['include_countries']]
        if 'exclude_countries' in prefs:
            filtered = [p for p in filtered if p.country not in prefs['exclude_countries']]

        # Minimum score threshold
        if 'min_score' in prefs:
            filtered = [p for p in filtered if p.heart_rate_score >= prefs['min_score']]

        return filtered

    def _enforce_geo_diversity(self, properties: List[Property]) -> List[Property]:
        """
        Ensure no cluster has more than 2 properties.
        Cluster = geographic area (postcode prefix or city).
        """
        cluster_counts = defaultdict(int)
        diverse = []

        # Sort by score descending
        sorted_props = sorted(properties, key=lambda p: p.heart_rate_score, reverse=True)

        for prop in sorted_props:
            cluster = self._get_cluster_key(prop)

            if cluster_counts[cluster] < 2:  # Max 2 per cluster
                diverse.append(prop)
                cluster_counts[cluster] += 1

        return diverse

    def _get_cluster_key(self, prop: Property) -> str:
        """
        Generate cluster key for geographic grouping.
        Uses postcode prefix if available, else city, else region.
        """
        if prop.postcode:
            return prop.postcode[:3]  # First 3 chars of postcode
        elif prop.city:
            return prop.city.upper()
        elif prop.region:
            return prop.region.upper()
        return prop.country

    def _pick_by_segment(self, properties: List[Property]) -> List[Property]:
        """
        Pick top candidate for each of the 6 show segments.
        Ensures we have one of each segment type.
        """
        selected = []
        used_ids = set()

        # Desired segment order (tweakable)
        desired_segments = [
            'The Sublime View',
            'The Authentic Bones',
            'The Sanctuary Plot',
            'The Quick Win',
            'The Unique Wonder',
            'The Balanced Gem',
        ]

        for segment in desired_segments:
            # Find best unscored property matching this segment
            best = None
            best_score = -1

            for prop in properties:
                if prop.id in used_ids:
                    continue

                if prop.get_segment() == segment:
                    if prop.heart_rate_score > best_score:
                        best = prop
                        best_score = prop.heart_rate_score

            if best:
                selected.append(best)
                used_ids.add(best.id)

        return selected

    def _pick_backups(self, all_properties: List[Property], selected: List[Property], count: int) -> List[Property]:
        """
        If ideal picks exhausted, grab highest-scoring remaining properties.
        Ensures we always have exactly 6.
        """
        selected_ids = {p.id for p in selected}
        backups = []

        sorted_props = sorted(all_properties, key=lambda p: p.heart_rate_score, reverse=True)

        for prop in sorted_props:
            if prop.id not in selected_ids and len(backups) < count:
                backups.append(prop)
                selected_ids.add(prop.id)

        return backups

    async def _find_nearby_episodes(self, selected: List[Property], radius_km: int = 20) -> Dict[int, List[Dict]]:
        """
        Find previously-shown properties within radius of each selected property.
        Returns dict mapping selected prop ID -> list of nearby past episodes.
        """
        nearby_map = {}

        for prop in selected:
            if not (prop.latitude and prop.longitude):
                continue

            # Haversine query in SQL (approximate for small distances)
            # 1 degree latitude ≈ 111km
            # For longitude: 1° = 111km * cos(latitude)
            lat_range = radius_km / 111.0
            lon_range = radius_km / (111.0 * abs(prop.latitude or 45))

            query = """
                SELECT sp.property_id, s.id as show_id, s.show_date,
                       p.title, p.price, p.city,
                       p.latitude, p.longitude
                FROM showed_properties sp
                JOIN shows s ON sp.show_id = s.id
                JOIN properties p ON sp.property_id = p.id
                WHERE p.latitude BETWEEN ? AND ?
                  AND p.longitude BETWEEN ?
                  AND ?
                  AND p.id != ?
                  AND p.is_still_for_sale = TRUE
                ORDER BY s.show_date DESC
                LIMIT 3
            """

            lat_min = prop.latitude - lat_range
            lat_max = prop.latitude + lat_range
            lon_min = prop.longitude - lon_range
            lon_max = prop.longitude + lon_range

            async with db.get_cursor() as cur:
                await cur.execute(query, (
                    lat_min, lat_max, lon_min, lon_max, prop.id
                ))
                rows = await cur.fetchall()
                nearby = [dict(row) for row in rows]
                if nearby:
                    nearby_map[prop.id] = nearby

        return nearby_map

    def segment_labels(self) -> List[str]:
        """Return the 6 show segment labels."""
        return [
            'The Sublime View',
            'The Authentic Bones',
            'The Sanctuary Plot',
            'The Quick Win',
            'The Unique Wonder',
            'The Balanced Gem',
        ]
