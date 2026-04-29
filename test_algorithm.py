#!/usr/bin/env python3
"""
Test script for Heart-Rate algorithm.
Verifies that properties score correctly across all 3 pillars.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from models.property import Property
from models.scorer import HeartRateScorer


def test_sublime_score():
    """Test Escapism Index calculation."""
    scorer = HeartRateScorer()

    # Property with sea view, large land
    p = Property()
    p.has_sea_view = True
    p.land_area_ha = 10
    p.neighbor_distance_m = 150
    p.price = 150000
    p.condition = 'habitable'

    score = scorer.score_property(p)
    assert p.sublime_escapism_score >= 60, f"Expected sublime >= 60, got {p.sublime_escapism_score}"
    print("✓ Sublime Escapism scoring works")

def test_authentic_score():
    """Test Authentic Bones calculation."""
    scorer = HeartRateScorer()

    p = Property()
    p.has_exposed_beams = True
    p.has_original_stone_floors = True
    p.has_structural_stone_walls = True
    p.has_functional_fireplaces = 2
    p.has_wooden_ceilings = True
    p.construction_year = 1850
    p.price = 120000
    p.condition = 'renovation_needed'

    score = scorer.score_property(p)
    assert p.authentic_bones_score >= 80, f"Expected authentic >= 80, got {p.authentic_bones_score}"
    print("✓ Authentic Bones scoring works")

def test_sanctuary_score():
    """Test Sanctuary Capacity calculation."""
    scorer = HeartRateScorer()

    p = Property()
    p.outbuilding_count = 3
    p.has_annex_potential = True
    p.plot_area_m2 = 2000
    p.has_separate_entrance = True
    p.is_set_back_from_road = True
    p.price = 180000
    p.condition = 'habitable'

    score = scorer.score_property(p)
    assert p.sanctuary_capacity_score >= 80, f"Expected sanctuary >= 80, got {p.sanctuary_capacity_score}"
    print("✓ Sanctuary Capacity scoring works")

def test_multiplier():
    """Test Manageable Project multiplier."""
    scorer = HeartRateScorer()

    # Too expensive → penalty
    p1 = Property()
    p1.price = 300000
    p1.condition = 'habitable'
    m1 = scorer._calc_multiplier(p1)
    assert m1 < 0.5, f"Expensive property should have low multiplier, got {m1}"

    # Affordable + habitable → no penalty
    p2 = Property()
    p2.price = 75000
    p2.condition = 'habitable'
    m2 = scorer._calc_multiplier(p2)
    assert m2 >= 0.9, f"Affordable habitable should have high multiplier, got {m2}"

    # Shell/ruin → major penalty
    p3 = Property()
    p3.price = 50000
    p3.condition = 'shell'
    m3 = scorer._calc_multiplier(p3)
    assert m3 <= 0.3, f"Shell condition should have very low multiplier, got {m3}"

    print("✓ Multiplier safety check works")

def test_segment_assignment():
    """Test that properties get assigned correct segments."""
    scorer = HeartRateScorer()

    # Sublime view property
    p1 = Property()
    p1.has_sea_view = True
    p1.price = 200000
    p1.condition = 'habitable'
    scorer.score_property(p1)
    assert p1.get_segment() == "The Sublime View", f"Should be Sublime View, got {p1.get_segment()}"

    # Authentic bones property
    p2 = Property()
    p2.has_exposed_beams = True
    p2.has_structural_stone_walls = True
    p2.has_functional_fireplaces = 2
    p2.price = 100000
    p2.condition = 'renovation_needed'
    scorer.score_property(p2)
    assert p2.get_segment() == "The Authentic Bones", f"Should be Authentic Bones, got {p2.get_segment()}"

    # Quick Win
    p3 = Property()
    p3.price = 65000
    p3.condition = 'habitable'
    p3.has_exposed_beams = True
    p3.authentic_bones_score = 70
    scorer.score_property(p3)
    assert p3.get_segment() == "The Quick Win", f"Should be Quick Win, got {p3.get_segment()}"

    print("✓ Segment assignment works")


async def test_full_scoring():
    """Test complete scoring pipeline."""
    scorer = HeartRateScorer()

    p = Property(
        agency_id=1,
        property_ref="TEST-001",
        listing_url="https://example.com/test",
        title="Beautiful Stone Farmhouse with Sea View",
        description=(
            "Stunning 19th century stone farmhouse with exposed beams, "
            "original terracotta floors, and 2 fireplaces. "
            "Panoramic sea views, 10 hectares of land, "
            "3 outbuildings including a separate barn. "
            "Habitable but needs modernization. "
            "Perfect for creating your dream retreat."
        ),
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

    scorer.score_property(p)

    print(f"\n🏠 Test Property: {p.title}")
    print(f"   Price: €{p.price:,.0f}")
    print(f"   Location: {p.city}, {p.region}, {p.country}")
    print(f"\n📊 Heart-Rate Scores:")
    print(f"   Sublime Escapism: {p.sublime_escapism_score}/100")
    print(f"   Authentic Bones:  {p.authentic_bones_score}/100")
    print(f"   Sanctuary Capacity: {p.sanctuary_capacity_score}/100")
    print(f"   Multiplier: {p.multiplier_score:.2f}x")
    print(f"   ⭐ FINAL SCORE: {p.heart_rate_score}/1000")
    print(f"\n   Segment: {p.get_segment()}")

    assert p.heart_rate_score > 400, f"Expected decent score, got {p.heart_rate_score}"
    print("\n✓ Full scoring pipeline works!")


def main():
    print("Running Heart-Rate Algorithm Tests\n")

    try:
        test_sublime_score()
        test_authentic_score()
        test_sanctuary_score()
        test_multiplier()
        test_segment_assignment()
        asyncio.run(test_full_scoring())

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED")
        print("="*50)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
