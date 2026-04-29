-- Daily Property Show Database Schema
-- Compatible with Cloudflare D1 (SQLite)

-- Agencies we scrape
CREATE TABLE agencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    website_url VARCHAR(500) NOT NULL,
    contact_email VARCHAR(200),
    key_contact VARCHAR(200),
    countries JSON DEFAULT '[]',
    regions JSON DEFAULT '[]',
    property_types JSON DEFAULT '[]',
    last_scraped TIMESTAMP,
    scrape_frequency_hours INTEGER DEFAULT 24,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Properties database (the core)
CREATE TABLE properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agency_id INTEGER NOT NULL,
    property_ref VARCHAR(100) NOT NULL,
    listing_url VARCHAR(1000) NOT NULL UNIQUE,

    -- Basic info
    title VARCHAR(300),
    description TEXT,

    -- Financial
    price DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'EUR',
    price_history JSON DEFAULT '[]',

    -- Physical
    bedrooms INTEGER,
    bathrooms INTEGER,
    property_type VARCHAR(50),
    condition VARCHAR(50),
    plot_area_m2 DECIMAL(10,2),
    living_area_m2 DECIMAL(10,2),
    land_area_ha DECIMAL(8,2),  -- for Escapism Index

    -- Location
    location_address TEXT,
    city VARCHAR(100),
    region VARCHAR(100),
    country VARCHAR(50),
    postcode VARCHAR(20),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    geo_cluster VARCHAR(100),  -- e.g., "lot-et-garonne-central"

    -- Heart-Rate scores (0-100 each)
    sublime_escapism_score INTEGER DEFAULT 0,
    authentic_bones_score INTEGER DEFAULT 0,
    sanctuary_capacity_score INTEGER DEFAULT 0,
    multiplier_score DECIMAL(3,2) DEFAULT 1.0,  -- 0.1-1.0
    heart_rate_score INTEGER DEFAULT 0,  -- final weighted score

    -- Feature flags (for algorithm)
    has_sea_view BOOLEAN DEFAULT FALSE,
    has_mountain_view BOOLEAN DEFAULT FALSE,
    has_valley_view BOOLEAN DEFAULT FALSE,
    neighbor_distance_m INTEGER DEFAULT 0,
    has_exposed_beams BOOLEAN DEFAULT FALSE,
    has_original_stone_floors BOOLEAN DEFAULT FALSE,
    has_functional_fireplaces INTEGER DEFAULT 0,
    has_structural_stone_walls BOOLEAN DEFAULT FALSE,
    has_wooden_ceilings BOOLEAN DEFAULT FALSE,
    construction_year INTEGER,
    outbuilding_count INTEGER DEFAULT 0,
    has_annex_potential BOOLEAN DEFAULT FALSE,
    has_pool BOOLEAN DEFAULT FALSE,
    has_separate_entrance BOOLEAN DEFAULT FALSE,
    is_set_back_from_road BOOLEAN DEFAULT FALSE,

    -- Images & media
    image_urls JSON DEFAULT '[]',
    primary_image_url VARCHAR(1000),
    has_floorplan BOOLEAN DEFAULT FALSE,
    has_video_tour BOOLEAN DEFAULT FALSE,

    -- Dates & tracking
    date_listed DATE,
    date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_still_for_sale BOOLEAN DEFAULT TRUE,
    featured_count INTEGER DEFAULT 0,  -- times selected for show

    -- Dupe detection
    fingerprint VARCHAR(500),  -- normalized address + price + beds
    UNIQUE(agency_id, property_ref),
    UNIQUE(listing_url)
);

-- Shows/episodes
CREATE TABLE shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_date DATE UNIQUE NOT NULL,
    episode_number INTEGER UNIQUE NOT NULL,
    youtube_id VARCHAR(20),
    title VARCHAR(200),
    description TEXT,
    video_url VARCHAR(500),
    published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Which properties in which show (with segment assignment)
CREATE TABLE show_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id INTEGER NOT NULL,
    property_id INTEGER NOT NULL,
    segment_order INTEGER NOT NULL,  -- 1-6
    segment_title VARCHAR(100),  -- "The Sublime View", etc.
    talking_points JSON,  -- Host's key points
    FOREIGN KEY (show_id) REFERENCES shows(id),
    FOREIGN KEY (property_id) REFERENCES properties(id),
    UNIQUE(show_id, segment_order)
);

-- Deduplication: what we've already shown
CREATE TABLE showed_properties (
    property_id INTEGER PRIMARY KEY,
    first_shown_in_show INTEGER NOT NULL,
    FOREIGN KEY (property_id) REFERENCES properties(id),
    FOREIGN KEY (first_shown_in_show) REFERENCES shows(id)
);

-- Price tracking
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id)
);

-- Scrape audit log
CREATE TABLE scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agency_id INTEGER NOT NULL,
    scrape_start TIMESTAMP NOT NULL,
    scrape_end TIMESTAMP,
    properties_found INTEGER DEFAULT 0,
    properties_new INTEGER DEFAULT 0,
    properties_updated INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running',  -- 'success', 'failed', 'partial'
    error_message TEXT,
    FOREIGN KEY (agency_id) REFERENCES agencies(id)
);

-- Your feedback on properties (for algorithm tuning)
CREATE TABLE curator_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    show_id INTEGER,  -- if reviewed in context of a show
    thumbs_up BOOLEAN,  -- NULL = no vote, TRUE = approve, FALSE = reject
    tags JSON DEFAULT '[]',  -- ["family-friendly", "bargain", "unique"]
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id),
    FOREIGN KEY (show_id) REFERENCES shows(id)
);

-- Indexes for performance
CREATE INDEX idx_properties_heart_score ON properties(heart_rate_score DESC);
CREATE INDEX idx_properties_agency ON properties(agency_id);
CREATE INDEX idx_properties_geo ON properties(geo_cluster);
CREATE INDEX idx_properties_fingerprint ON properties(fingerprint);
CREATE INDEX idx_properties_last_verified ON properties(last_verified);
CREATE INDEX idx_showed_properties ON showed_properties(property_id);
CREATE INDEX idx_shows_date ON shows(show_date);

-- Views for common queries
CREATE VIEW v_recent_properties AS
SELECT p.*, a.name as agency_name
FROM properties p
JOIN agencies a ON p.agency_id = a.id
WHERE p.last_verified > datetime('now', '-7 days')
  AND p.is_still_for_sale = TRUE
ORDER BY p.heart_rate_score DESC;

CREATE VIEW v_available_for_show AS
SELECT p.*
FROM properties p
WHERE p.last_verified > datetime('now', '-3 days')
  AND p.is_still_for_sale = TRUE
  AND p.id NOT IN (SELECT property_id FROM showed_properties WHERE property_id IS NOT NULL);
