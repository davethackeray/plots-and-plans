#!/usr/bin/env python3
"""
Simple test for Heart-Rate algorithm - Windows compatible.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models.property import Property
from models.scorer import HeartRateScorer

print("Testing Heart-Rate Algorithm...")
scorer = HeartRateScorer()

# Test 1: Sublime property
p1 = Property()
p1.has_sea_view = True
p1.land_area_ha = 10
p1.price = 150000
p1.condition = 'habitable'
scorer.score_property(p1)
assert p1.sublime_escapism_score >= 60
print("✓ Sublime Escapism works")

# Test 2: Authentic property
p2 = Property()
p2.has_exposed_beams = True
p2.has_structural_stone_walls = True
p2.has_functional_fireplaces = 2
p2.price = 100000
p2.condition = 'renovation_needed'
scorer.score_property(p2)
assert p2.authentic_bones_score >= 70
print("✓ Authentic Bones works")

# Test 3: Sanctuary property
p3 = Property()
p3.outbuilding_count = 3
p3.has_annex_potential = True
p3.plot_area_m2 = 2000
p3.price = 180000
p3.condition = 'habitable'
scorer.score_property(p3)
assert p3.sanctuary_capacity_score >= 70
print("✓ Sanctuary Capacity works")

# Test 4: Full property
p4 = Property(
    agency_id=1,
    property_ref="TEST-001",
    listing_url="https://example.com/test",
    title="Beautiful Stone Farmhouse with Sea View",
    description="Stunning 19th century stone farmhouse with exposed beams, original terracotta floors, and 2 fireplaces. Panoramic sea views, 10 hectares of land, 3 outbuildings including a separate barn. Habitable but needs modernization.",
    price=125000,
    currency='EUR',
    bedrooms=4,
    bathrooms=2,
    property_type='farmhouse',
    condition='renovation_needed',
    city="Saint-Cyprien",
    region="Dordogne",
    country="France",
    latitude=44.888,
    longitude=0.123,
    land_area_ha=10.5,
    plot_area_m2=5000,
)
scorer.score_property(p4)
print(f"\nTest Property Score: {p4.heart_rate_score}/1000")
print(f"Segment: {p4.get_segment()}")
assert p4.heart_rate_score > 400
print("✓ Full scoring pipeline works!")

print("\nAll tests passed!")
