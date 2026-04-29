"""
Database connection management.
Async SQLite interface (compatible with Cloudflare D1).
"""

import aiosqlite
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, List, Any


class Database:
    """Async database connection manager."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or "database/properties.db"
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")
        print(f"✓ Connected to database: {self.db_path}")
        return self

    async def close(self):
        if self._conn:
            await self._conn.close()

    @asynccontextmanager
    async def get_cursor(self):
        """Context manager for DB operations."""
        cursor = await self._conn.cursor()
        try:
            yield cursor
        finally:
            await cursor.close()

    async def insert(self, query: str, params: tuple = None) -> int:
        async with self.get_cursor() as cur:
            await cur.execute(query, params or ())
            await self._conn.commit()
            return cur.lastrowid

    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        async with self.get_cursor() as cur:
            await cur.execute(query, params or ())
            row = await cur.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        async with self.get_cursor() as cur:
            await cur.execute(query, params or ())
            return [dict(row) for row in await cur.fetchall()]

    async def execute(self, query: str, params: tuple = None):
        async with self.get_cursor() as cur:
            await cur.execute(query, params or ())
            await self._conn.commit()


# Global instance
db = Database()


def row_to_dict(row: aiosqlite.Row) -> Dict:
    """Convert row to dict, parsing JSON fields."""
    if row is None:
        return {}
    d = dict(row)
    json_fields = ['countries', 'regions', 'property_types', 'image_urls',
                   'price_history', 'talking_points', 'fingerprint']
    for field in json_fields:
        if field in d and d[field]:
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


async def init_database():
    """Initialize DB connection."""
    await db.connect()


async def get_connection():
    """Get database connection."""
    if db._conn is None:
        await db.connect()
    return db
