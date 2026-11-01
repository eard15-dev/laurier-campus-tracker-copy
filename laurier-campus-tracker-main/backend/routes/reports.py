from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request

from database import get_db
from services.calculations import utc_now_string

bp = Blueprint("reports", __name__)


def is_rating(value):
    # bool is a kind of int in python, so True would pass without the second check
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5


def get_int_arg(name, minimum=None, maximum=None):
    # returns (value, error). value is None if the param wasn't given
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None, None
    try:
        value = int(raw)
    except ValueError:
        return None, name + " must be a whole number"
    if minimum is not None and (value < minimum or value > maximum):
        return None, f"{name} must be between {minimum} and {maximum}"
    return value, None


@bp.post("/reports")
def create_report():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify(error="Request body must be a non-empty JSON object"), 400

    location_id = data.get("location_id")
    noise = data.get("noise_level")
    busyness = data.get("busyness_level")

    if not isinstance(location_id, int) or isinstance(location_id, bool):
        return jsonify(error="location_id must be an integer"), 400
    if not is_rating(noise):
        return jsonify(error="noise_level must be an integer from 1 to 5"), 400
    if not is_rating(busyness):
        return jsonify(error="busyness_level must be an integer from 1 to 5"), 400

    db = get_db()
    if db.execute("SELECT 1 FROM locations WHERE id = ?", (location_id,)).fetchone() is None:
        return jsonify(error="Location not found"), 404

    # rate limit: remember when each device last reported each space (in memory)
    now = datetime.now(timezone.utc)
    limit = timedelta(minutes=current_app.config["RATE_LIMIT_MINUTES"])
    last_times = current_app.extensions.setdefault("last_report_times", {})
    for old_key in [k for k, t in last_times.items() if now - t >= limit]:
        del last_times[old_key]
    key = (request.remote_addr, location_id)
    if key in last_times:
        seconds = int((limit - (now - last_times[key])).total_seconds()) + 1
        return jsonify(error=f"You already reported this space recently. Try again in {seconds} seconds."), 429

    cursor = db.execute(
        "INSERT INTO reports (location_id, noise_level, busyness_level, created_at) VALUES (?, ?, ?, ?)",
        (location_id, noise, busyness, utc_now_string()),
    )
    db.commit()
    last_times[key] = now
    return jsonify(message="Report submitted successfully", report_id=cursor.lastrowid), 201


@bp.post("/reports/<int:report_id>/flag")
def flag_report(report_id):
    db = get_db()
    cursor = db.execute("UPDATE reports SET flag_count = flag_count + 1 WHERE id = ?", (report_id,))
    if cursor.rowcount == 0:
        return jsonify(error="Report not found"), 404
    db.commit()
    count = db.execute("SELECT flag_count FROM reports WHERE id = ?", (report_id,)).fetchone()[0]
    hidden = count >= current_app.config["FLAG_THRESHOLD"]
    return jsonify(message="Report flagged", report_id=report_id, flag_count=count, hidden=hidden)


@bp.get("/reports")
def list_reports():
    location_id, error = get_int_arg("location_id")
    if error:
        return jsonify(error=error), 400
    noise, error = get_int_arg("noise_level", 1, 5)
    if error:
        return jsonify(error=error), 400
    busyness, error = get_int_arg("busyness_level", 1, 5)
    if error:
        return jsonify(error=error), 400
    limit, error = get_int_arg("limit", 1, 500)
    if error:
        return jsonify(error=error), 400
    building = request.args.get("building", "").strip()

    sql = ("SELECT r.*, l.name AS location_name, l.building FROM reports r "
           "JOIN locations l ON l.id = r.location_id WHERE 1=1")
    params = []
    if location_id is not None:
        sql += " AND r.location_id = ?"
        params.append(location_id)
    if noise is not None:
        sql += " AND r.noise_level = ?"
        params.append(noise)
    if busyness is not None:
        sql += " AND r.busyness_level = ?"
        params.append(busyness)
    if building:
        sql += " AND LOWER(l.building) = LOWER(?)"
        params.append(building)
    sql += " ORDER BY r.created_at DESC, r.id DESC LIMIT ?"
    params.append(limit or 100)

    rows = get_db().execute(sql, params).fetchall()
    return jsonify(reports=[dict(row) for row in rows], count=len(rows))
