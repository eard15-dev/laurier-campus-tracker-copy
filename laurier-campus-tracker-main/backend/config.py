import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "campus_tracker.db"))
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # reports older than this many minutes don't count as current
    REPORT_WINDOW_MINUTES = int(os.environ.get("REPORT_WINDOW_MINUTES", 60))
    # fewer recent reports than this = insufficient_data
    MIN_REPORTS = int(os.environ.get("MIN_REPORTS", 3))

    # average below LOW_MAX = first label, below MODERATE_MAX = middle label, else last label
    LOW_MAX = 2.5
    MODERATE_MAX = 3.5

    FLAG_THRESHOLD = int(os.environ.get("FLAG_THRESHOLD", 3))
    RATE_LIMIT_MINUTES = int(os.environ.get("RATE_LIMIT_MINUTES", 5))
    TIMEZONE = os.environ.get("TIMEZONE", "America/Toronto")
    SEED_SAMPLE_DATA = os.environ.get("SEED_SAMPLE_DATA", "1") == "1"

    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", 5000))
