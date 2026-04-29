#!/usr/bin/env python3
"""
Production Sheet Generator
Creates filming-ready CSV with all property details, Google Maps links,
and suggested talking points for each segment.
"""

import argparse
import asyncio
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Ensure import works from CLI
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from selector.engine import PropertySelector


class ProductionSheetGenerator:
    """Generates production-ready CSV for video filming."""

    SEGMENT_ORDER = [
        'The Sublime View',
        'The Authentic Bones',
        'The Sanctuary Plot',
        'The Quick Win',
        'The Unique Wonder',
        'The Balanced Gem',
    ]

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    async def generate_for_date(
        self,
        target_date: datetime,
        include_backups: bool = True,
        format: str = 'csv'
    ) -> Path:
        """
        Generate complete production package for given date.
        Returns path to generated file.
        """
        selector = PropertySelector()
        selection = await selector.select_for_date(target_date)

        if 'error' in selection:
            raise ValueError(f"Selection failed: {selection['error']}")

        date_str = target_date.strftime('%Y-%m-%d')
        filename = f"production-sheet-{date_str}.{format}"
        output_path = self.output_dir / filename

        # Build CSV rows
        rows = self._build_csv_rows(selection)

        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"✅ Production sheet saved: {output_path}")
        print(f"   Properties: {len(selection['selected'])}")
        print(f"   Avg score: {selection['metadata']['avg_score']:.0f}/1000")

        # Also generate JSON for programmatic access
        json_path = self.output_dir / f"production-{date_str}.json"
        with open(json_path, 'w') as f:
            json.dump(selection, f, indent=2, default=str)

        return output_path

    def _build_csv_rows(self, selection: Dict) -> List[List[str]]:
        """Build CSV rows from selection data."""
        props = selection['selected']
        nearby = selection.get('nearby_episodes', {})

        # Header
        rows = [
            [
                'Segment', 'Title', 'Price (EUR)', 'Beds', 'Baths',
                'City', 'Region', 'Country',
                'Heart Score', 'Sublime', 'Authentic', 'Sanctuary',
                'Listing URL', 'Primary Image', 'Nearby Episodes',
                'Talking Points', 'Google Maps Link'
            ]
        ]

        for i, prop in enumerate(props):
            segment = prop.get('segment', f'Property {i+1}')
            nearby_eps = nearby.get(prop['id'], [])
            nearby_text = ', '.join(str(e['show_id']) for e in nearby_eps[:2])

            # Generate Google Maps link
            maps_url = ""
            if prop.get('latitude') and prop.get('longitude'):
                maps_url = f"https://www.google.com/maps?q={prop['latitude']},{prop['longitude']}"
            elif prop.get('city'):
                maps_url = f"https://www.google.com/maps/search/?api=1&query={prop['city'].replace(' ', '+')}"

            # Auto-generated talking points
            points = self._generate_talking_points(prop)

            rows.append([
                segment,
                prop['title'][:80],
                f"{prop['price']:,.0f}" if prop.get('price') else "N/A",
                prop.get('bedrooms', 'N/A'),
                prop.get('bathrooms', 'N/A'),
                prop.get('city', ''),
                prop.get('region', ''),
                prop.get('country', ''),
                prop['heart_rate_score'],
                prop['scores']['sublime'],
                prop['scores']['authentic'],
                prop['scores']['sanctuary'],
                prop['listing_url'],
                prop.get('primary_image', ''),
                nearby_text,
                points,
                maps_url,
            ])

        # Add backup properties as separate section
        if 'backup_pool' in selection and selection['backup_pool']:
            rows.append([])  # blank line
            rows.append(['--- BACKUP PROPERTIES ---', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''])
            for backup in selection['backup_pool']:
                rows.append([
                    'BACKUP',
                    backup['title'][:80],
                    f"{backup['price']:,.0f}" if backup.get('price') else "N/A",
                    backup.get('bedrooms', 'N/A'),
                    backup.get('bathrooms', 'N/A'),
                    backup.get('city', ''),
                    backup.get('region', ''),
                    backup.get('country', ''),
                    backup['heart_rate_score'],
                    backup['scores']['sublime'],
                    backup['scores']['authentic'],
                    backup['scores']['sanctuary'],
                    backup['listing_url'],
                    backup.get('primary_image', ''),
                    '',
                    'Backup if primary fails',
                    '',
                ])

        return rows

    def _generate_talking_points(self, prop: Dict) -> str:
        """Auto-generate talking points based on scores."""
        points = []

        scores = prop['scores']
        seg = prop.get('segment', '')

        # Segment-specific hooks
        if 'Sublime' in seg:
            if prop.get('has_sea_view'):
                points.append("Sea view - impossible to install later")
            if scores['sublime'] >= 80:
                points.append("Panoramic vistas dominate the experience")

        if 'Authentic' in seg:
            if prop.get('has_exposed_beams'):
                points.append("Original beams - instant character")
            if prop.get('has_structural_stone_walls'):
                points.append("Solid stone construction - built to last")
            if prop.get('has_functional_fireplaces', 0) >= 2:
                points.append("Multiple fireplaces - cozy in multiple rooms")

        if 'Sanctuary' in seg:
            if prop.get('outbuilding_count', 0) >= 2:
                points.append("Multiple outbuildings - endless possibilities")
            if prop.get('has_annex_potential'):
                points.append("Separate entrance - perfect for gite/rental")

        if 'Quick Win' in seg:
            points.append("Cosmetic renovation only - fast turnaround")
            points.append("Already habitable - live while you renovate")

        if 'Unique' in seg:
            points.append("One-of-a-kind property - rare opportunity")

        if 'Balanced' in seg:
            points.append("No major compromises - ready to enjoy")

        # Price/affordability hook
        price = prop.get('price', 0)
        if price and price < 80000:
            points.append(f"Under €{price/1000:.0f}k - exceptional value")
        elif price and price < 150000:
            points.append(f"€{price/1000:.0f}k range - accessible luxury")

        return ' • '.join(points[:3])  # Top 3 points


async def main():
    parser = argparse.ArgumentParser(description='Generate daily production sheet.')
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD), default: today')
    parser.add_argument('--output', type=str, default='output', help='Output directory')
    parser.add_argument('--format', type=str, default='csv', choices=['csv', 'json'])

    args = parser.parse_args()

    if args.date:
        target = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target = datetime.now()

    generator = ProductionSheetGenerator(output_dir=args.output)

    try:
        path = await generator.generate_for_date(
            target_date=target,
            format=args.format
        )
        print(f"\n📄 Production sheet: {path}")
        print("\nNext steps:")
        print("1. Review properties in the sheet")
        print("2. Swap any that don't feel right (use dashboard)")
        print("3. Download images for filming")
        print("4. Record show with Google Earth walks")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
