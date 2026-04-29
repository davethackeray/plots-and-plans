"""
Database initialization script.
Creates tables from schema.sql and seeds agencies.
Run: python -m database.init_db
"""

import asyncio
import sqlite3
from pathlib import Path
import json

DB_PATH = Path(__file__).parent.parent / "database" / "properties.db"


async def init():
    """Initialize SQLite database with schema and seed data."""
    from aiosqlite import connect

    db_file = str(DB_PATH)
    conn = await connect(db_file)
    cursor = await conn.cursor()

    # Read and execute schema
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, encoding='utf-8') as f:
        schema_sql = f.read()
        await cursor.executescript(schema_sql)
        print("✓ Schema created")

    # Seed agencies
    agencies = load_agencies()
    for agency in agencies:
        await cursor.execute("""
            INSERT OR REPLACE INTO agencies (
                name, website_url, contact_email, key_contact,
                countries, regions, property_types, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
        """, (
            agency['name'],
            agency['website_url'],
            agency['contact_email'],
            agency['key_contact'],
            json.dumps(agency['countries']),
            json.dumps(agency['regions']),
            json.dumps(agency['property_types']),
        ))


    await conn.close()

    print(f"✓ Database initialized at {db_file}")
    print(f"✓ {len(agencies)} agencies seeded")


def load_agencies():
    """Load agency data from JSON file or hard-coded list."""
    # Try to load from agencies.json if exists
    agencies_json = Path(__file__).parent / "agencies.json"
    if agencies_json.exists():
        with open(agencies_json) as f:
            return json.load(f)

    # Fallback to hard-coded list (13 agencies)
    return [
        {
            "name": "Tuscanitas",
            "website_url": "https://www.tuscanitas.com",
            "contact_email": "divinetuscany@gmail.com",
            "key_contact": "Pier Paolo Giglioni (CEO)",
            "countries": ["Italy"],
            "regions": ["Tuscany", "Umbria", "Siena", "Montepulciano"],
            "property_types": ["farmhouse", "villa", "palace", "winery"]
        },
        {
            "name": "Beaux Villages Immobilier",
            "website_url": "https://www.beauxvillages.com",
            "contact_email": "info@beauxvillages.com",
            "key_contact": "Rob & Lynn Longley (Founders)",
            "countries": ["France"],
            "regions": ["Dordogne", "Lot", "Charente", "Aveyron", "Haute-Vienne"],
            "property_types": ["farmhouse", "village_house", "manor", "chateau"]
        },
        {
            "name": "Romantic Houses",
            "website_url": "https://www.romantichouses.com",
            "contact_email": "info@romantichouses.com",
            "key_contact": "Silvana Raffaghello (Founder)",
            "countries": ["Italy"],
            "regions": ["Le Marche", "Umbria"],
            "property_types": ["farmhouse", "village_house", "cottage"]
        },
        {
            "name": "Marche Country Homes",
            "website_url": "https://www.marchecountryhomes.com",
            "contact_email": "info@mch.it",
            "key_contact": "Lorenza Cappanera",
            "countries": ["Italy"],
            "regions": ["Le Marche"],
            "property_types": ["farmhouse", "country_house", "ruin"]
        },
        {
            "name": "Case in Langa",
            "website_url": "https://www.caseinlanga.it",
            "contact_email": "info@caseinlanga.it",
            "key_contact": "Martino Maria Rosa",
            "countries": ["Italy"],
            "regions": ["Piedmont", "Langa"],
            "property_types": ["farmhouse", "vineyard", "cottage"]
        },
        {
            "name": "Agenzia Il Casale",
            "website_url": "https://www.agenziailcasale.it",
            "contact_email": "ilcasale@tin.it",
            "key_contact": "Daniele Paolucci",
            "countries": ["Italy"],
            "regions": ["Tuscany", "Siena"],
            "property_types": ["farmhouse", "villa", "estate"]
        },
        {
            "name": "Aldeas Abandonadas",
            "website_url": "https://www.aldeasabandonadas.com",
            "contact_email": "info@sacapartido.com",
            "key_contact": "Elvira Fafian Novoa (Director)",
            "countries": ["Spain"],
            "regions": ["Andalusia", "Granada", "Almeria"],
            "property_types": ["cortijo", "village_house", "ruin"]
        },
        {
            "name": "Buscomasia",
            "website_url": "https://www.buscomasia.com",
            "contact_email": "info@buscomasia.com",
            "key_contact": "Adrià (Contact)",
            "countries": ["Spain"],
            "regions": ["Catalonia", "Girona"],
            "property_types": ["masia", "farmhouse", "country_estate"]
        },
        {
            "name": "Lançois Doval",
            "website_url": "https://www.lancoisdoval.es",
            "contact_email": "robert@lancoisdoval.es",
            "key_contact": "Robert Menetray (Managing Director)",
            "countries": ["Spain"],
            "regions": ["Aragon", "Huesca", "Pyrenees"],
            "property_types": ["farmhouse", "mountain_property", "village_house"]
        },
        {
            "name": "Gaia Inmobiliaria Rural",
            "website_url": "https://www.gaiainmobiliariarural.com",
            "contact_email": "web@gaiainmobiliariarural.com",
            "key_contact": "Lía Barros (Founder)",
            "countries": ["Spain"],
            "regions": ["Galicia", "Northern Spain"],
            "property_types": ["stone_house", "village_house", "farm"]
        },
        {
            "name": "Rustica Estates",
            "website_url": "https://www.rusticaestates.com",
            "contact_email": "rusticaestates1@gmail.com",
            "key_contact": "Sebastián Jarillo Moreno",
            "countries": ["Spain"],
            "regions": ["Andalusia", "Malaga", "Granada"],
            "property_types": ["cortijo", "farmhouse", "ruin"]
        },
        {
            "name": "Rusur",
            "website_url": "https://www.rusur.es",
            "contact_email": "info@sacapartido.com",
            "key_contact": "Manuel Ávila",
            "countries": ["Spain"],
            "regions": ["Extremadura", "Cáceres"],
            "property_types": ["village_house", "farmhouse", "estate"]
        },
        {
            "name": "PortugalRur",
            "website_url": "https://www.portugalrur.pt",
            "contact_email": "geral@portugalrur.pt",
            "key_contact": "Sócio Gerente (CEO)",
            "countries": ["Portugal"],
            "regions": ["Alentejo", "Algarve", "Silver Coast"],
            "property_types": ["quinta", "farmhouse", "country_house"]
        },
        {
            "name": "Entreportas",
            "website_url": "https://www.entreportas.pt",
            "contact_email": "vianamarina@entreportas.pt",
            "key_contact": "Carlos Rebelo (Commercial Director)",
            "countries": ["Portugal"],
            "regions": ["Algarve", "Loulé"],
            "property_types": ["villa", "townhouse", "apartment"]
        }
    ]


if __name__ == "__main__":
    asyncio.run(init())
