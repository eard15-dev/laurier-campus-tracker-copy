import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    building TEXT NOT NULL,
    floor TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL REFERENCES locations(id),
    noise_level INTEGER NOT NULL CHECK (noise_level BETWEEN 1 AND 5),
    busyness_level INTEGER NOT NULL CHECK (busyness_level BETWEEN 1 AND 5),
    created_at TEXT NOT NULL,
    flag_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_reports_location_time ON reports (location_id, created_at);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # sqlite has this off by default
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path, seed_sample_data=True):
    conn = connect(path)
    conn.executescript(SCHEMA)
    if seed_sample_data:
        from seed import seed_locations
        seed_locations(conn)
    conn.commit()
    conn.close()
