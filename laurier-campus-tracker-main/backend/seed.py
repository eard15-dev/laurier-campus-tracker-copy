# SAMPLE DATA ONLY - these are made up, not real Laurier locations.
# Run with: python seed.py
from config import Config
from database import connect, init_db

SAMPLE_LOCATIONS = [
    ("Sample Study Room A", "Sample Building 1", "Floor 1", "SAMPLE DATA - not a real Laurier location"),
    ("Sample Study Room B", "Sample Building 1", "Floor 2", "SAMPLE DATA - not a real Laurier location"),
    ("Sample Library Commons", "Sample Building 2", "Floor 1", "SAMPLE DATA - not a real Laurier location"),
    ("Sample Quiet Lounge", "Sample Building 2", "Floor 3", "SAMPLE DATA - not a real Laurier location"),
]


def seed_locations(conn):
    count = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO locations (name, building, floor, description) VALUES (?, ?, ?, ?)",
            SAMPLE_LOCATIONS,
        )


if __name__ == "__main__":
    init_db(Config.DATABASE, seed_sample_data=True)
    conn = connect(Config.DATABASE)
    total = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    print("Database ready:", Config.DATABASE, "-", total, "locations")
