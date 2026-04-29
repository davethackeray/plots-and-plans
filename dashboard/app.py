"""
Admin Dashboard - Daily property review interface.
Run with: python -m dashboard.app
Access at: http://localhost:5000
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import json

from database import db
from models.property import Property
from selector.engine import PropertySelector
from notifier.bot import TelegramNotifier

app = FastAPI(title="Daily Property Show Dashboard")

# Mount static files (CSS/JS)
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

# DB path (local dev)
DB_PATH = "daily-show-system/database/properties.db"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard home - today's picks."""
    today = datetime.now()
    show_date = today.strftime('%Y-%m-%d')

    # Get today's selection (or generate if not exists)
    selector = PropertySelector()
    try:
        selection = await selector.select_for_date(today)
        props = selection['selected']
        meta = selection['metadata']
    except Exception as e:
        props = []
        meta = {'error': str(e)}

    return templates.TemplateResponse("index.html", {
        "request": request,
        "properties": props,
        "date": show_date,
        "metadata": meta,
    })


@app.get("/api/properties/today")
async def get_today_properties():
    """JSON API for today's picks."""
    today = datetime.now()
    selector = PropertySelector()
    selection = await selector.select_for_date(today)
    return selection


@app.post("/api/properties/swap")
async def swap_property(segment: int, new_property_id: int):
    """
    Replace property at segment position with another candidate.
    Segment: 1-6, new_property_id: from backup pool
    """
    # This would update the selection in a persistent store
    # For now, just log the swap request
    print(f"Swap requested: segment {segment} with property {new_property_id}")
    return {"status": "ok", "message": "Swap recorded (not yet persistent)"}


@app.get("/api/properties/nearby/{property_id}")
async def get_nearby(property_id: int):
    """Get previously-shown properties near this one."""
    # Query DB for nearby
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get property coords
    cur.execute("SELECT latitude, longitude FROM properties WHERE id = ?", (property_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Property not found")

    lat, lon = row['latitude'], row['longitude']
    if not (lat and lon):
        return {"nearby": []}

    # Haversine approx (20km radius)
    lat_range = 20 / 111.0
    lon_range = 20 / (111.0 * abs(lat))

    cur.execute("""
        SELECT p.*, s.show_date, s.id as show_id
        FROM showed_properties sp
        JOIN shows s ON sp.show_id = s.id
        JOIN properties p ON sp.property_id = p.id
        WHERE p.latitude BETWEEN ? AND ?
          AND p.longitude BETWEEN ? AND ?
          AND p.id != ?
        ORDER BY s.show_date DESC
        LIMIT 3
    """, (lat - lat_range, lat + lat_range, lon - lon_range, lon + lon_range, property_id))

    nearby = [dict(row) for row in cur.fetchall()]
    conn.close()
    return {"nearby": nearby}


@app.get("/production-sheet/{date}")
async def get_production_sheet(date: str):
    """Generate production-ready CSV for given date."""
    target = datetime.strptime(date, '%Y-%m-%d')
    selector = PropertySelector()
    selection = await selector.select_for_date(target)

    # Generate CSV content
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Segment', 'Title', 'Price', 'Location', 'URL', 'Heart Score'])

    for i, prop in enumerate(selection['selected']):
        writer.writerow([
            i + 1,
            prop['title'],
            prop['price'],
            f"{prop['city']}, {prop['country']}",
            prop['listing_url'],
            prop['heart_rate_score'],
        ])

    return {
        "csv": output.getvalue(),
        "filename": f"production-sheet-{date}.csv"
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Daily Property Show Dashboard")
    print("   http://localhost:5000")
    print("   Press Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)
