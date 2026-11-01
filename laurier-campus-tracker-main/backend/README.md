# Laurier Campus Tracker – Backend (CP317A, Sprint 01)

## 1. What the backend does
A small REST API that stores **student-submitted reports** about how noisy and busy campus study spaces are, and turns recent reports into a "current conditions" summary. There are no sensors: all data comes from students. If fewer than 3 reports exist in the last 60 minutes, the API says `insufficient_data` instead of guessing.

> The 4 locations in the database are **SAMPLE DATA** (see `seed.py`), not real Laurier spaces. Replace them when the team has real ones.

## 2. Technologies
Python 3, Flask (API), Flask-CORS (lets React call the API), SQLite via Python's built-in `sqlite3`, pytest (tests), JSON.

## 3. How the database works
SQLite stores everything in one file, `backend/campus_tracker.db`, created automatically on first start (and ignored by Git).

| Table | Columns |
|---|---|
| `locations` | `id` (PK), `name`, `building`, `floor`, `description` |
| `reports` | `id` (PK), `location_id` (FK → locations), `noise_level` 1–5, `busyness_level` 1–5, `created_at` (UTC, e.g. `2026-10-27T16:30:00Z`) |

- Foreign keys are switched on for every connection (`PRAGMA foreign_keys = ON`).
- All SQL uses `?` placeholders, never string-pasted values, to prevent SQL injection.
- To reset: stop the server and delete `campus_tracker.db`.

### How conditions are calculated
- Only reports from the last `REPORT_WINDOW_MINUTES` (default **60**) count.
- Need at least `MIN_REPORTS` (default **3**) recent reports, otherwise `status` is `"insufficient_data"` and averages/labels are `null`.
- Labels from the average rating (our initial choice, not a course requirement): average **below 2.5** = first label, **2.5 up to 3.5** = middle label, **3.5 and above** = last label.
  - Noise: `quiet` / `moderate` / `loud`
  - Busyness: `low` / `medium` / `high`
- Reports flagged 3 times (`FLAG_THRESHOLD`) are hidden from conditions and trends.
- The same device can report on the same space once every 5 minutes (`RATE_LIMIT_MINUTES`, kept in memory; 429 if too soon).

## 4. Create and activate a virtual environment (macOS)
```bash
cd laurier-campus-tracker/backend
python3 -m venv .venv
source .venv/bin/activate      # prompt now shows (.venv)
```
Leave it later with `deactivate`.

## 5. Install dependencies
```bash
pip install -r requirements.txt
```

## 6. Start the server
```bash
python app.py
```
API base URL: **http://127.0.0.1:5000/api**. The database is created and filled with sample locations automatically. (`python seed.py` does the same by hand.)

### Settings (environment variables, all optional)
| Variable | Default | Meaning |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated React origins allowed to call the API |
| `REPORT_WINDOW_MINUTES` | `60` | How old a report can be and still count |
| `MIN_REPORTS` | `3` | Reports needed before showing averages |
| `FLAG_THRESHOLD` | `3` | Flags needed to hide a report |
| `RATE_LIMIT_MINUTES` | `5` | Minutes between reports per device per space (0 = off) |
| `TIMEZONE` | `America/Toronto` | Used to group reports into morning/midday/afternoon/evening |
| `DATABASE_PATH` | `backend/campus_tracker.db` | Database file |
| `PORT` | `5000` | Server port |

Example: `CORS_ORIGINS=http://localhost:4000 MIN_REPORTS=2 python app.py`

## 7. API reference and how to test each endpoint
Run these in a second terminal while the server is running.

All errors look like `{"error": "message"}`. Codes: 200 OK, 201 created, 400 invalid input, 404 not found, 500 server error.

### GET /api/health
```bash
curl http://127.0.0.1:5000/api/health
```
`{"status": "ok"}`

### GET /api/locations
Lists locations, each with a `status` object. Optional filters, combined with AND:

| Param | Values | How it works |
|---|---|---|
| `search` | text | Space name or building contains the text, case-insensitive (the search box) |
| `building` | text | Exact match on building name, case-insensitive |
| `noise` | `quiet`, `moderate`, `loud` | Keeps locations whose *current* average noise has that label |
| `busyness` | `low`, `medium`, `high` | Same, for busyness |

Locations with `insufficient_data` have no label, so they are **excluded** when `noise` or `busyness` is used. Any other value for `noise`/`busyness` returns 400.
```bash
curl http://127.0.0.1:5000/api/locations
curl "http://127.0.0.1:5000/api/locations?search=library&noise=quiet"
```
```json
{
  "count": 1,
  "locations": [{
    "id": 1, "name": "Sample Study Room A", "building": "Sample Building 1",
    "floor": "Floor 1", "description": "SAMPLE DATA - not a real Laurier location",
    "status": {
      "status": "ok", "recent_report_count": 3, "window_minutes": 60,
      "min_reports_required": 3, "latest_report_at": "2026-10-27T20:35:52Z",
      "average_noise": 2.0, "average_busyness": 4.0,
      "noise_label": "quiet", "busyness_label": "high"
    }
  }]
}
```

### GET /api/locations/<id>
```bash
curl http://127.0.0.1:5000/api/locations/1
```
Returns the location, or 404 `{"error": "Location not found"}`.

### GET /api/locations/<id>/status
```bash
curl http://127.0.0.1:5000/api/locations/1/status
```
Same `status` fields as above plus `location_id`. With too few reports: `"status": "insufficient_data"`, averages and labels `null`.

### GET /api/locations/<id>/reports
Reports inside the time window for that location, newest first.
```bash
curl http://127.0.0.1:5000/api/locations/1/reports
```
`{"count": 3, "reports": [{"id": 3, "location_id": 1, "noise_level": 2, "busyness_level": 4, "created_at": "..."}]}`

### GET /api/buildings
`{"buildings": ["Sample Building 1", "Sample Building 2"]}` - for the Building filter.

### GET /api/locations/<id>/trends
Typical busyness by time of day for the Usage Trends screen. Periods (Toronto time): morning 5-11, midday 11-14, afternoon 14-18, evening 18-5. A period needs 3+ reports to get an average; quietest/busiest need 2+ periods with averages, otherwise `"status": "insufficient_data"`.
```json
{"location_id": 1, "status": "ok", "quietest_period": "morning", "busiest_period": "afternoon",
 "periods": [{"period": "morning", "report_count": 5, "average_busyness": 1.4, "busyness_label": "low"}]}
```

### POST /api/reports/<id>/flag
The "Flag a suspicious report" button. Returns `{"message": "Report flagged", "report_id": 1, "flag_count": 1, "hidden": false}`; 404 if the report does not exist.

### POST /api/reports
```bash
curl -X POST http://127.0.0.1:5000/api/reports \
  -H "Content-Type: application/json" \
  -d '{"location_id": 1, "noise_level": 2, "busyness_level": 4}'
```
201: `{"message": "Report submitted successfully", "report_id": 1}`

The frontend's 3 buttons can send 1 / 3 / 5 (Quiet/Moderate/Loud, Low/Medium/High). Returns 429 if the same device reported this space within the last 5 minutes.

Rejected with 400: empty/malformed JSON, non-object JSON, `location_id` not an integer, ratings that are not integers 1–5 (strings, decimals, booleans, out of range). Rejected with 404 if the location does not exist.

### GET /api/reports
All reports (not limited to the time window), newest first, with `location_name` and `building`. Optional exact-match filters, combined with AND: `location_id`, `building`, `noise_level` (1–5), `busyness_level` (1–5), `limit` (1–500, default 100). Invalid values return 400.
```bash
curl "http://127.0.0.1:5000/api/reports?noise_level=2&limit=10"
```

## 8. Connecting the React frontend
Base URL: `http://127.0.0.1:5000/api`. CORS is enabled for `http://localhost:5173` (Vite) and `http://localhost:3000` (Create React App); change with `CORS_ORIGINS`. Start the backend and the React app at the same time.

```js
const API = "http://127.0.0.1:5000/api";

// List locations (with filters)
const res = await fetch(`${API}/locations?building=${encodeURIComponent("Sample Building 1")}&noise=quiet`);
const { locations } = await res.json();

// One location's current conditions
const status = await (await fetch(`${API}/locations/1/status`)).json();
if (status.status === "insufficient_data") { /* show "Not enough recent reports" */ }

// Submit a report
const response = await fetch(`${API}/reports`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ location_id: 1, noise_level: 2, busyness_level: 4 }),
});
const result = await response.json();
if (!response.ok) console.error(result.error); // e.g. "noise_level must be an integer from 1 to 5"
```

## 9. Run the automated tests
```bash
cd backend
source .venv/bin/activate
python -m pytest -v
```
Each test uses its own temporary database, so your real database is never changed.

## 10. Troubleshooting
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: flask` | Activate the venv (`source .venv/bin/activate`) and run `pip install -r requirements.txt` |
| `Address already in use` (port 5000) | macOS AirPlay uses 5000 on some Macs. Use `PORT=5001 python app.py` and update the frontend URL |
| Browser says "blocked by CORS policy" | Add your React URL to `CORS_ORIGINS` and restart the server |
| `python: command not found` | Use `python3`, or activate the venv first |
| Want a fresh database | Stop the server, delete `campus_tracker.db`, start again |
| Locations show `insufficient_data` | Expected: submit 3 reports within an hour (or lower `MIN_REPORTS` while developing) |

## What each file does
| File | Purpose |
|---|---|
| `app.py` | Starts Flask, turns on CORS, creates the database, registers the routes, and makes all errors return JSON. `create_app()` lets tests build an app with a temporary database. |
| `config.py` | All settings in one place (CORS origins, time window, minimum reports, label thresholds), read from environment variables. |
| `database.py` | Opens SQLite connections (foreign keys on), defines the two tables, and creates them at startup. |
| `seed.py` | Adds the clearly-labelled sample locations when the table is empty. |
| `routes/locations.py` | The `/api/locations...` endpoints and the building/noise/busyness filters. |
| `routes/reports.py` | `POST /api/reports` (validation, rate limit, saving), `POST /api/reports/<id>/flag`, and `GET /api/reports` (filters). |
| `services/calculations.py` | The math: picks recent reports, averages them, returns `insufficient_data` or labels, and builds the time-of-day trends. |
| `tests/` | pytest tests; `conftest.py` builds a temporary database and helper functions. |
