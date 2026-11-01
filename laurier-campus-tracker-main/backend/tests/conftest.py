import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from database import connect  # noqa: E402
from services.calculations import TIME_FORMAT  # noqa: E402


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        "SEED_SAMPLE_DATA": False,
        "REPORT_WINDOW_MINUTES": 60,
        "MIN_REPORTS": 3,
        "FLAG_THRESHOLD": 3,
        "RATE_LIMIT_MINUTES": 0,
    })
    conn = connect(app.config["DATABASE"])
    conn.executemany(
        "INSERT INTO locations (name, building, floor, description) VALUES (?, ?, ?, ?)",
        [
            ("Room A", "North Hall", "1", "test"),
            ("Room B", "North Hall", "2", "test"),
            ("Room C", "South Hall", "1", "test"),
        ],
    )
    conn.commit()
    conn.close()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def add_report(app):
    def _add(location_id, noise, busyness, minutes_ago=0, when=None):
        when = when or datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        conn = connect(app.config["DATABASE"])
        conn.execute(
            "INSERT INTO reports (location_id, noise_level, busyness_level, created_at) VALUES (?, ?, ?, ?)",
            (location_id, noise, busyness, when.strftime(TIME_FORMAT)),
        )
        conn.commit()
        conn.close()
    return _add
